import os
import uuid
import time
import shutil
import logging
import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.settings import settings
from core.pdf_parser import extract_text_from_pdf
from core.job_search import search_jobs
from core.db import get_db_connection, set_cache, get_cache, init_db
from routers import auth, interview, vision, identity, hub
from agents.graph import run_analysis
from agents.improver import improve_resume
from core.telemetry import TelemetryLogger
from core.guardrails import scan_prompt_injection
from core.mlflow_tracker import mlflow_tracker
from core.student_model import psi_student
import hashlib
from core.digital_twin import CandidateDigitalTwin, RecruiterDigitalTwin
from core.fairness import BiasAuditor, CounterfactualCalibrator, RobustnessEvaluator
from core.model_router import ModelGatewayRouter
from core.event_bus import EventBus
from core.mcp_sandbox import MCPSandbox

logger = logging.getLogger("psi_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PSI Resume Analyser API",
    description="Enterprise API backing the React resume scanning & matching application.",
    version="1.0.0"
)


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(interview.router, tags=["interview"])
app.include_router(vision.router, tags=["vision_streaming"])
app.include_router(identity.router)
app.include_router(hub.router, prefix="/api/hub", tags=["hub"])

# Enable CORS – read allowed origins from environment variable
# Default to "*" for local development; set ALLOWED_ORIGINS in production
_allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "*")
_allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

allow_origins = []
allow_origin_regex = None

regex_patterns = []
for origin in _allowed_origins:
    if origin == "*":
        allow_origins = ["*"]
        break
    elif "*" in origin:
        # Convert wildcard domain to regex pattern
        pattern = re.escape(origin).replace(r"\*", r"[^/]*")
        regex_patterns.append(f"^{pattern}$")
    else:
        allow_origins.append(origin)

if regex_patterns:
    allow_origin_regex = "|".join(regex_patterns)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Temporary directory for uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Models
class ImproveRequest(BaseModel):
    resume_text: str
    jd_text: str

class StressTestRequest(BaseModel):
    prompt: str

class CheckoutRequest(BaseModel):
    cardholder: str
    card_number: str
    expiry: str
    cvv: str
    amount: float = 49.0


# --- Endpoints ---

SAMPLE_JD_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_jds")

@app.get("/api/sample-jds")
def get_sample_jds():
    samples = []
    if os.path.exists(SAMPLE_JD_DIR) and os.path.isdir(SAMPLE_JD_DIR):
        files = sorted([f for f in os.listdir(SAMPLE_JD_DIR) if f.endswith(".txt")])
        for i, filename in enumerate(files, 1):
            filepath = os.path.join(SAMPLE_JD_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                
                label = os.path.splitext(filename)[0].replace("_", " ").title()
                title = label
                company = "Enterprise"
                location = "Hybrid/Remote"
                
                # Parse headers from the first few lines
                lines = text.split("\n")
                for line in lines[:8]:
                    line_lower = line.lower()
                    if line_lower.startswith("job title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line_lower.startswith("company:"):
                        company = line.split(":", 1)[1].strip()
                    elif line_lower.startswith("location:"):
                        location = line.split(":", 1)[1].strip()
                
                samples.append({
                    "id": f"JD #{i}",
                    "friendly_name": label,
                    "title": title,
                    "company": company,
                    "location": location,
                    "filename": filename,
                    "text": text
                })
            except Exception as e:
                logger.error(f"Failed to read sample JD {filename}: {e}")
    return samples


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.head("/")
def head_root():
    from fastapi import Response
    return Response(status_code=200)



@app.post("/api/admin/distill")
async def trigger_student_distillation(user_id: Optional[str] = Depends(auth.get_current_user)):
    """Triggers the Teacher-Student Distillation pipeline to train the local PSI Student model."""
    try:
        success = psi_student.train_student()
        if success:
            return {"message": "PSI Student Model successfully distilled from LLM teacher outputs."}
        else:
            raise HTTPException(status_code=400, detail="Insufficient training data for distillation.")
    except Exception as e:
        logger.error(f"Distillation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run distillation: {str(e)}")


@app.post("/api/analyze")
async def analyze_endpoint(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    premium_mode: bool = Form(False),
    user_id: Optional[str] = Depends(auth.get_current_user)
):
    start_time = time.time()
    
    # Verify file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save upload file to temporary location
    temp_file_id = str(uuid.uuid4())
    temp_filepath = os.path.join(UPLOAD_DIR, f"{temp_file_id}.pdf")
    
    try:
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")
        
    try:
        # Extract text from PDF
        resume_text = extract_text_from_pdf(temp_filepath)
        if not resume_text or len(resume_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract readable text from PDF resume.")
        
        # Check for prompt injection in resume
        is_inj, conf, reason = scan_prompt_injection(resume_text)
        if is_inj:
            # Record failed telemetry event
            latency = time.time() - start_time
            TelemetryLogger.record_event(
                node_name="guardrail_scan",
                provider="groq",
                latency_sec=latency,
                prompt_tokens=0,
                completion_tokens=0,
                status="failed",
                error_msg=f"Prompt injection blocked: {reason}"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Security Block: Adversarial prompt detected in resume.",
                    "details": reason
                }
            )
            
        # Run Multi-Agent Graph Analysis
        analysis_result = run_analysis(
            resume_text=resume_text,
            jd_text=jd_text,
            pdf_path=temp_filepath,
            premium_mode=premium_mode
        )
        
        if "error" in analysis_result and analysis_result["error"]:
            raise HTTPException(status_code=500, detail=analysis_result["error"])
            
        # Log to MLflow Observability Registry
        mlflow_tracker.log_analysis_run(temp_file_id, analysis_result)
            
        # Write analysis run details to SQLite database
        run_id = temp_file_id
        conn = get_db_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO analysis_runs 
            (id, timestamp, resume_name, match_score, keyword_score, semantic_score, details) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                file.filename,
                float(analysis_result.get("match_score", 0.0)),
                float(analysis_result.get("keyword_score", 0.0)),
                float(analysis_result.get("semantic_score", 0.0)),
                json.dumps(analysis_result)
            )
        )
        
        # Sync telemetry event logs
        latency = time.time() - start_time
        conn.execute(
            """
            INSERT INTO telemetry_logs 
            (timestamp, provider, input_tokens, output_tokens, cost, latency, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                "groq", # Default or extracted provider
                0, # Counted at agent layer
                0,
                TelemetryLogger.calculate_cost("groq", 1000, 500), # Simulated placeholder
                latency,
                "success"
            )
        )
        
        # MLOps continuous data loop logging
        if settings.data_loop.enable_data_loop:
            conn.execute(
                """
                INSERT INTO finetuning_dataset 
                (timestamp, instruction, input, output) 
                VALUES (?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    f"Evaluate resume for JD: {jd_text[:100]}...",
                    json.dumps({"resume": resume_text[:1000], "jd": jd_text[:1000]}),
                    json.dumps(analysis_result)
                )
            )
            
        conn.commit()
        conn.close()
        
        # Push to MongoDB User Memory if authenticated
        if user_id:
            try:
                from core.mongo_db import get_db
                mongo_db = get_db()
                if mongo_db is not None:
                    memory_entry = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "resume_name": file.filename,
                        "match_score": analysis_result.get("match_score"),
                        "analysis": analysis_result
                    }
                    # Keep only the latest 15 resumes to prevent extreme document bloat
                    mongo_db.users.update_one(
                        {"user_id": user_id},
                        {
                            "$push": {
                                "memory": {
                                    "$each": [memory_entry],
                                    "$slice": -15
                                }
                            }
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to save to MongoDB memory: {e}")
        
        # Record Drift and Telemetry Metrics
        try:
            from core.drift_monitor import DriftMonitor
            from core.metrics import record_analysis_metrics
            
            skills_analysis = analysis_result.get("skills_analysis", {})
            if isinstance(skills_analysis, dict):
                skill_count = len(skills_analysis.get("matched_skills", [])) + len(skills_analysis.get("missing_skills", []))
            else:
                skill_count = 0
            
            score = float(analysis_result.get("match_score", 0.0))
            
            # Record run for statistical drift
            DriftMonitor.record_run(
                resume_text=resume_text,
                jd_text=jd_text,
                skill_count=skill_count,
                composite_score=score
            )
            
            # Record Prometheus metrics
            duration = time.time() - start_time
            record_analysis_metrics(
                status="success",
                duration=duration,
                tokens_in=0,
                tokens_out=0,
                is_premium=premium_mode
            )
        except Exception as m_err:
            logger.warning(f"Failed to record run metrics in API: {m_err}")
        
        return analysis_result
        
    except Exception as ex:
        # Record failed analysis run metrics
        try:
            from core.metrics import record_analysis_metrics
            duration = time.time() - start_time
            record_analysis_metrics(
                status="error",
                duration=duration,
                is_premium=premium_mode
            )
        except Exception:
            pass
        logger.exception("API analysis failed")
        raise HTTPException(status_code=500, detail=str(ex))
    finally:
        # Clean up temp file
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_filepath}: {e}")
                
        # Aggressive memory optimization for Render Free Tier
        try:
            from core.embeddings import unload_model
            unload_model()
        except Exception:
            pass
        import gc
        gc.collect()


@app.post("/api/improve")
def improve_endpoint(req: ImproveRequest):
    try:
        # Heuristically split resume_text into individual bullets
        raw_lines = req.resume_text.split("\n")
        existing_bullets = []
        for line in raw_lines:
            line_clean = line.strip().lstrip("*-•0123456789. ")
            if line_clean:
                existing_bullets.append(line_clean)
        
        if not existing_bullets:
            existing_bullets = [req.resume_text.strip()]

        # Construct the Graph State dict
        state = {
            "resume_parsed": {
                "experience": [{"bullets": existing_bullets}]
            },
            "jd_extracted": {
                "job_title": "Target Role",
                "required_skills": [req.jd_text[:100]] if req.jd_text else [],
                "responsibilities": [req.jd_text[:200]] if req.jd_text else []
            },
            "skill_match": {},
            "gaps": ["Add quantitative metrics and business impact"],
            "strengths": [],
            "overall_score": 50.0
        }
        
        # Call the core multi-agent node
        result = improve_resume(state)
        
        # Check if result has error or if it failed
        if not result or result.get("error"):
            logger.warning("Improver agent returned error or empty response. Falling back to heuristic optimizer.")
            # Heuristic enhancement fallback
            optimized = []
            for b in existing_bullets:
                improved = b
                if not any(word in b.lower() for word in ["spearheaded", "architected", "delivered", "optimized", "increased", "reduced"]):
                    improved = "Optimized and delivered: " + b
                if not any(char.isdigit() for char in b):
                    improved += " — achieving a 20% improvement in performance and delivery metrics."
                optimized.append({"original": b, "improved": improved})
        else:
            optimized = result.get("ats_optimized_bullets", [])
            
        # Extract plain strings
        improved_list = []
        for b in optimized:
            improved_bullet = b.get("improved", "") if isinstance(b, dict) else b
            if improved_bullet:
                improved_list.append(improved_bullet)
                
        # Fallback if empty
        if not improved_list:
            improved_list = existing_bullets
            
        joined_bullets = "\n".join(improved_list)
        return {"improved_bullets": joined_bullets}
        
    except Exception as e:
        logger.exception("Improve bullets failed")
        # Fallback to avoid 500 error
        try:
            heuristic_bullets = []
            for line in req.resume_text.split("\n"):
                line_clean = line.strip().lstrip("*-•0123456789. ")
                if line_clean:
                    heuristic_bullets.append(line_clean)
            if not heuristic_bullets:
                heuristic_bullets = [req.resume_text]
            return {"improved_bullets": "\n".join(heuristic_bullets), "error": str(e)}
        except Exception:
            raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/jobs")
def get_jobs_endpoint(
    location: str = "",
    remote_only: bool = False,
    query: str = "Software Engineer"
):
    cache_key = f"jobs_search_{query.lower()}_{location.lower()}_{remote_only}"
    cached = get_cache(cache_key)
    if cached:
        logger.info("Serving job listings from cache.")
        return cached

    try:
        # 1. Generate search queries heuristically or using LLM
        # For simplicity, search using queries directly
        jobs = search_jobs(queries=[query], location=location, remote_only=remote_only)
        
        # Fallback to sample listings if empty
        if not jobs:
            # Mock / fallback listings to ensure deck isn't empty
            from core.job_search import JobListing
            jobs = [
                JobListing(
                    title=f"Senior {query}",
                    company="Tech Corp Industries",
                    location=location or "Remote",
                    description=f"Looking for a Senior {query} with extensive Python backend expertise, Docker containers, and CI/CD pipelines.",
                    url="https://example.com/apply-1",
                    salary="$120,000 - $150,000",
                    source="Fallback Engine",
                    remote=True
                ),
                JobListing(
                    title=f"Junior {query}",
                    company="Startup Growth Hub",
                    location=location or "San Francisco, CA",
                    description=f"Grow your career as a Junior {query}. Working with React frontend interfaces, FastAPIs, and relational databases.",
                    url="https://example.com/apply-2",
                    salary="$80,000 - $100,000",
                    source="Fallback Engine",
                    remote=False
                )
            ]

        # 2. Extract job listing dicts
        res_list = []
        for j in jobs:
            res_list.append({
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description": j.description,
                "url": j.url,
                "salary": j.salary,
                "source": j.source,
                "posted_date": j.posted_date,
                "job_type": j.job_type,
                "tags": j.tags,
                "remote": j.remote
            })
            
            # Cache in SQLite database jobs table as well
            try:
                conn = get_db_connection()
                job_id = f"{j.title}_{j.company}".lower().replace(" ", "_")
                conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs_cache 
                    (id, title, company, location, description, url, salary, source, posted_date, job_type, tags, remote) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id, j.title, j.company, j.location, j.description, j.url, j.salary, j.source, j.posted_date, j.job_type, ",".join(j.tags), 1 if j.remote else 0
                    )
                )
                conn.commit()
                conn.close()
            except Exception as dberr:
                logger.warning(f"Failed to cache job in DB: {dberr}")

        # Set cache
        set_cache(cache_key, res_list, expire_seconds=1800)
        return res_list
        
    except Exception as e:
        logger.exception("Failed to search jobs")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/telemetry")
def get_telemetry_endpoint():
    try:
        # Load aggregates from database
        conn = get_db_connection()
        total_runs_row = conn.execute("SELECT COUNT(*) FROM telemetry_logs").fetchone()
        avg_latency_row = conn.execute("SELECT AVG(latency) FROM telemetry_logs").fetchone()
        total_cost_row = conn.execute("SELECT SUM(cost) FROM telemetry_logs").fetchone()
        
        ft_count_row = conn.execute("SELECT COUNT(*) FROM finetuning_dataset").fetchone()
        
        recent_logs_cursor = conn.execute("SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT 20")
        recent_logs = [dict(row) for row in recent_logs_cursor.fetchall()]
        
        recent_runs_cursor = conn.execute("SELECT id, timestamp, resume_name, match_score FROM analysis_runs ORDER BY timestamp DESC LIMIT 20")
        recent_runs = [dict(row) for row in recent_runs_cursor.fetchall()]
        
        conn.close()
        
        total_runs = total_runs_row[0] if total_runs_row else 0
        avg_latency = round(avg_latency_row[0], 2) if avg_latency_row and avg_latency_row[0] else 0.0
        total_cost = round(total_cost_row[0], 4) if total_cost_row and total_cost_row[0] else 0.0
        ft_count = ft_count_row[0] if ft_count_row else 0

        # Retrieve file-based logs fallback if DB is empty
        summary = TelemetryLogger.get_summary_metrics()
        
        return {
            "total_runs": total_runs or summary.get("total_runs", 0),
            "total_cost_usd": total_cost or summary.get("total_cost_usd", 0.0),
            "average_latency_sec": avg_latency or summary.get("average_latency_sec", 0.0),
            "dataset_size": ft_count,
            "recent_logs": recent_logs or TelemetryLogger.get_recent_logs(20),
            "recent_runs": recent_runs
        }
    except Exception as e:
        logger.exception("Failed to query telemetry logs")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/checkout")
def checkout_endpoint(req: CheckoutRequest):
    try:
        session_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO payment_sessions (session_id, timestamp, cardholder, amount, status) VALUES (?, ?, ?, ?, ?)",
            (session_id, datetime.now(timezone.utc).isoformat(), req.cardholder, req.amount, "approved")
        )
        conn.commit()
        conn.close()
        return {"status": "approved", "session_id": session_id, "amount": req.amount}
    except Exception as e:
        logger.exception("Checkout failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stress-test")
def stress_test_endpoint(req: StressTestRequest):
    try:
        is_inj, conf, reason = scan_prompt_injection(req.prompt)
        return {
            "prompt_injection_detected": is_inj,
            "confidence": conf,
            "reason": reason
        }
    except Exception as e:
        logger.exception("Stress test failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def get_metrics_endpoint():
    from fastapi import Response
    from core.metrics import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/digital_twin")
def get_digital_twin(run_id: str, jd_text: Optional[str] = None):
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT details FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        conn.close()
        
        if not row:
            conn = get_db_connection()
            row = conn.execute("SELECT details FROM analysis_runs ORDER BY timestamp DESC LIMIT 1").fetchone()
            conn.close()

        if row:
            analysis = json.loads(row["details"])
            resume_parsed = analysis.get("resume_parsed", {})
            if not jd_text:
                jd_text = analysis.get("jd_text", "Software Developer Developer Python JavaScript Git")
        else:
            resume_parsed = {
                "name": "Jane Doe (Default Blueprint)",
                "skills": ["python", "fastapi", "pytorch", "docker", "kubernetes", "sql"],
                "experience": [
                    {
                        "title": "Senior Cloud Developer",
                        "bullets": [
                            "Led migration of microservices to Kubernetes clusters.",
                            "Optimized database performance by 35% through query indexes."
                        ]
                    }
                ]
            }
            if not jd_text:
                jd_text = "Software Developer Developer Python JavaScript Git"
            
        candidate_twin = CandidateDigitalTwin.construct_twin(resume_parsed)
        recruiter_twin = RecruiterDigitalTwin.simulate_screening(resume_parsed, jd_text)
        
        return {
            "run_id": run_id,
            "candidate_twin": candidate_twin,
            "recruiter_twin": recruiter_twin
        }
    except Exception as e:
        logger.exception("Failed to build digital twins")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fairness_audit")
def get_fairness_audit(run_id: str):
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT details FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        conn.close()
        
        if not row:
            conn = get_db_connection()
            row = conn.execute("SELECT details FROM analysis_runs ORDER BY timestamp DESC LIMIT 1").fetchone()
            conn.close()

        if row:
            analysis = json.loads(row["details"])
            resume_text = analysis.get("resume_text", "")
            if not resume_text:
                bullets_list = []
                for exp in analysis.get("resume_parsed", {}).get("experience", []):
                    bullets_list.extend(exp.get("bullets", []))
                resume_text = "\n".join(bullets_list) or "John Doe Resume Python Developer"
            
            skills = analysis.get("resume_parsed", {}).get("skills", [])
            score = float(analysis.get("match_score", 50.0))
        else:
            resume_text = "Jane Doe. Email: jane.doe@gmail.com. AWS Certified. 10 years experience."
            skills = ["python", "fastapi", "pytorch", "docker", "kubernetes"]
            score = 78.5

        audit = BiasAuditor.audit_demographics(resume_text)
        calibration = CounterfactualCalibrator.what_if_analysis(score, skills, resume_text)
        robustness = RobustnessEvaluator.audit_robustness(resume_text, score)

        return {
            "run_id": run_id,
            "bias_audit": audit,
            "counterfactual_calibration": calibration,
            "robustness_audit": robustness
        }
    except Exception as e:
        logger.exception("Failed to run fairness audit")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clearance_metrics")
def get_clearance_metrics():
    try:
        router = ModelGatewayRouter(tenant_tier="enterprise")
        event_bus = EventBus()
        mcp_client = MCPSandbox()
        
        route1 = router.route_request("graph_rag", 12000)
        route2 = router.route_request("bias_audit", 2000)
        route3 = router.route_request("improver", 500)
        
        event_bus.subscribe("parse_event", lambda p: logger.info("Parse complete"))
        event_bus.publish("parse_event", {"resume_id": "test_id"})
        event_bus.publish("score_event", {"score": 82.5})
        
        sig1 = hashlib.sha256("github/list_repos:default_enterprise".encode()).hexdigest()[:16]
        mcp_client.execute_tool("github/list_repos", {"org": "google"}, sig1)
        mcp_client.execute_tool("ats/update_candidate_status", {"candidate_id": "c1", "status": "; rm -rf /"}, "invalidsig")

        return {
            "model_routing": {
                "tenant_tier": router.tenant_tier,
                "current_session_cost_usd": router.spent_usd,
                "budget_cap_usd": router.max_budget_usd,
                "history": [
                    {"task": "GraphRAG Node Retrieval", "model": route1["model_name"], "cost": route1["estimated_cost_usd"], "truncated": route1["context_truncated"]},
                    {"task": "Bias Demographic Audit", "model": route2["model_name"], "cost": route2["estimated_cost_usd"], "truncated": route2["context_truncated"]},
                    {"task": "STAR Bullet Improvement", "model": route3["model_name"], "cost": route3["estimated_cost_usd"], "truncated": route3["context_truncated"]}
                ]
            },
            "event_bus": {
                "events_processed": len(event_bus.get_audit_trail()),
                "audit_trail": [
                    {"event_id": ev["event_id"], "event_type": ev["event_type"], "status": ev["status"], "retries": ev["retry_count"]} 
                    for ev in event_bus.get_audit_trail()
                ]
            },
            "mcp_sandbox": {
                "allowlisted_tools": list(MCPSandbox.ALLOWLIST_TOOLS),
                "audit_trail": [
                    {"tool": call["tool_name"], "status": call["status"], "reason": call["reason"], "timestamp": call["timestamp"]}
                    for call in mcp_client.get_audit_trail()
                ]
            }
        }
    except Exception as e:
        logger.exception("Failed to retrieve clearance metrics")
        raise HTTPException(status_code=500, detail=str(e))


# --- Serve React App static files ---
dist_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.exists(dist_path):
    # Serve assets folder
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    # Serve index.html fallback for client-side routing
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Prevent shadowing API endpoints
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "Not Found"})
            
        file_path = os.path.join(dist_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_path, "index.html"))
else:
    @app.get("/")
    def index_placeholder():
        return {
            "message": "FastAPI is running. Frontend static directory 'frontend/dist' was not found. Please build the React app using 'npm run build'."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=7860, reload=True)
