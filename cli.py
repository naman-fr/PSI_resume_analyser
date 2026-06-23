"""
PSI Resume Analyser - Command Line Interface (CLI)
Provides command-terminal access to the multi-agent cognitive ATS pipeline,
job finder, bullet improver, telemetry, and security scanners.
"""

import os
import sys
import glob
import json
import logging
import click

logger = logging.getLogger("psi_cli")

# Ensure current directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Third-party imports handled gracefully
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.markdown import Markdown
    from rich import box
    from rich.syntax import Syntax  # noqa: F401
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Simple fallback console
    class SimpleConsole:
        def print(self, *args, **kwargs):
            print(*args)
        def log(self, *args, **kwargs):
            print("[LOG]", *args)
    Console = SimpleConsole

console = Console()

# Core pipeline imports
try:
    from core.pdf_parser import extract_text_from_pdf
    from core.job_search import search_jobs
    from core.job_matcher import score_jobs
    from core.job_query_generator import generate_search_queries
    from agents.graph import run_analysis
    from agents.improver import improve_resume
    from core.telemetry import TelemetryLogger
    from core.guardrails import scan_prompt_injection
    from core.drift_monitor import DriftMonitor
    PIPELINE_LOADED = True
except Exception as e:
    PIPELINE_LOADED = False
    PIPELINE_ERROR = e


def read_text_or_pdf(file_path: str) -> str:
    """Read document text either from a PDF or plain text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        if not PIPELINE_LOADED:
            raise RuntimeError(f"Pipeline modules failed to load: {PIPELINE_ERROR}")
        return extract_text_from_pdf(file_path)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


@click.group()
def cli():
    """PSI Resume Analyser: Cognitive ATS Terminal Masterclass"""
    pass


@cli.command()
@click.argument("resume_file", type=click.Path(exists=True))
@click.option("--jd", help="Job description text directly in terminal")
@click.option("--jd-file", type=click.Path(exists=True), help="Path to text file containing job description")
@click.option("--premium", is_flag=True, help="Enable Premium Intelligence Suite scans")
@click.option("--output", type=click.Choice(["text", "json", "csv"]), default="text", help="Format of output results")
@click.option("--save-report", type=click.Path(), help="Path to save the generated analysis report")
def analyze(resume_file, jd, jd_file, premium, output, save_report):
    """Run full LangGraph multi-agent scan on a PDF/text resume against a JD."""
    if not PIPELINE_LOADED:
        console.print(Panel(f"[bold red]Error:[/] Core pipeline modules could not be imported.\nDetail: {PIPELINE_ERROR}", title="Pipeline Load Failure"))
        sys.exit(1)

    # Get JD text
    jd_content = ""
    if jd:
        jd_content = jd
    elif jd_file:
        with open(jd_file, "r", encoding="utf-8", errors="ignore") as f:
            jd_content = f.read()
    else:
        console.print("[bold yellow]Warning:[/] No Job Description provided. Searching/extracting default keywords.")
        jd_content = "Software Engineer Developer Python JavaScript SQL Git Agile Cloud Docker CI/CD API"

    try:
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description="Extracting text from resume...", total=None)
                resume_text = read_text_or_pdf(resume_file)
                
                progress.add_task(description="Running cognitive multi-agent pipeline...", total=None)
                result = run_analysis(
                    resume_text=resume_text,
                    jd_text=jd_content,
                    pdf_path=resume_file if resume_file.lower().endswith(".pdf") else None,
                    premium_mode=premium
                )
        else:
            resume_text = read_text_or_pdf(resume_file)
            result = run_analysis(
                resume_text=resume_text,
                jd_text=jd_content,
                pdf_path=resume_file if resume_file.lower().endswith(".pdf") else None,
                premium_mode=premium
            )

        if "error" in result and result["error"]:
            console.print(f"[bold red]Pipeline Error:[/] {result['error']}")
            sys.exit(1)

        # Output formatting
        if output == "json":
            click.echo(json.dumps(result, indent=2))
        elif output == "csv":
            import csv
            import io
            f = io.StringIO()
            w = csv.writer(f)
            w.writerow(["Metric", "Value"])
            w.writerow(["Match Score", result.get("match_score", 0.0)])
            w.writerow(["Keyword Score", result.get("keyword_score", 0.0)])
            w.writerow(["Semantic Score", result.get("semantic_score", 0.0)])
            w.writerow(["Invisible Text Flagged", result.get("invisible_text_flagged", False)])
            click.echo(f.getvalue())
        else:
            # Text / Rich output
            score = float(result.get("match_score", 0.0))
            color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
            
            console.print("\n")
            console.print(Panel(
                f"[bold]Candidate Name:[/] {result.get('resume_parsed', {}).get('name', 'N/A')}\n"
                f"[bold]Email:[/] {result.get('resume_parsed', {}).get('email', 'N/A')}\n"
                f"[bold]Score:[/] [{color}]{score:.1f}%[/]\n"
                f"[bold]Keyword Overlap:[/] {result.get('keyword_score', 0.0):.1f}%\n"
                f"[bold]Semantic Alignment:[/] {result.get('semantic_score', 0.0):.1f}%",
                title=f"[bold]Analysis Report for {os.path.basename(resume_file)}[/]",
                subtitle="PHANTOM COGNITIVE ATS ENGINE",
                box=box.DOUBLE
            ))

            # Strengths Panel
            strengths = result.get("strengths", [])
            strengths_text = "\n".join(f"  - {s}" for s in strengths) if strengths else "  - None identified."
            console.print(Panel(strengths_text, title="[bold green]Strengths & Alignments[/]", border_style="green"))

            # Gaps & Missing Skills Panel
            gaps = result.get("gaps", [])
            missing_skills = result.get("skill_match", {}).get("missing", []) if isinstance(result.get("skill_match"), dict) else []
            
            gaps_text = "[bold red]Identified Gaps:[/]\n" + ("\n".join(f"  - {g}" for g in gaps) if gaps else "  - No major gaps identified.")
            if missing_skills:
                gaps_text += "\n\n[bold yellow]Missing Skills / Keywords:[/]\n  " + ", ".join(missing_skills)
            console.print(Panel(gaps_text, title="[bold red]Gap Analysis & Gaps[/]", border_style="red"))

            # Bullet suggestions
            bullets = result.get("ats_optimized_bullets", [])
            if bullets:
                bullets_text = ""
                for b in bullets[:5]:
                    improved_bullet = b.get("improved", "") if isinstance(b, dict) else b
                    bullets_text += f"  - {improved_bullet}\n"
                console.print(Panel(bullets_text.strip(), title="[bold blue]ATS-Optimized Bullet Suggestions (STAR Framework)[/]", border_style="blue"))

            # Premium Report if available
            if premium and "premium_report" in result:
                report = result["premium_report"]
                console.print(Panel(
                    f"[bold]Integrity Check:[/] {'[bold red]FLAGGED[/]' if result.get('invisible_text_flagged') else '[bold green]PASSED[/]'}\n"
                    f"[bold]Consistency Index:[/] {report.get('consistency_index', 'N/A')}\n"
                    f"[bold]Hiring Readiness:[/] {report.get('hiring_readiness', 'N/A')}\n"
                    f"[bold]Trust Score (URLs):[/] {result.get('links_verification', {}).get('trust_score', 'N/A')}%",
                    title="[bold yellow]Premium Analytics Suite[/]",
                    border_style="yellow"
                ))

        if save_report:
            with open(save_report, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            console.print(f"[bold green]Success:[/] Saved JSON report to {save_report}")

    except Exception as e:
        console.print(f"[bold red]Analysis failed:[/] {e}")
        logger.exception("CLI Analysis command failed")
        sys.exit(1)


@cli.command()
@click.option("--resume-text", help="Resume text directly")
@click.option("--resume-file", type=click.Path(exists=True), help="Path to resume file (PDF or text)")
@click.option("--bullets", help="Comma-separated bullet points to improve directly")
def improve(resume_text, resume_file, bullets):
    """Optimize resume bullet points using the STAR framework."""
    if not PIPELINE_LOADED:
        console.print(f"[bold red]Error:[/] Pipeline modules failed: {PIPELINE_ERROR}")
        sys.exit(1)

    try:
        existing_bullets = []
        if bullets:
            existing_bullets = [b.strip() for b in bullets.split(",") if b.strip()]
        elif resume_file:
            text = read_text_or_pdf(resume_file)
            # Basic bullet extraction heuristics
            existing_bullets = [line.strip().lstrip("*-") for line in text.split("\n") if line.strip().startswith(("*", "-"))]
            if not existing_bullets:
                # Fallback to lines that look like work experience
                existing_bullets = [line.strip() for line in text.split("\n") if len(line.strip()) > 30 and len(line.strip()) < 150][:5]
        elif resume_text:
            existing_bullets = [line.strip().lstrip("*-") for line in resume_text.split("\n") if len(line.strip()) > 20][:5]
        else:
            console.print("[bold yellow]Info:[/] No bullets or resume provided. Improving sample backend engineer bullets.")
            existing_bullets = [
                "Responsible for writing python APIs.",
                "Worked on database optimization.",
                "Fixed bugs and wrote test cases."
            ]

        console.print(f"Improving {len(existing_bullets)} bullets with STAR Optimizer...\n")

        # Mock up a State object for improve_resume node
        state = {
            "resume_parsed": {
                "experience": [{"bullets": existing_bullets}]
            },
            "jd_extracted": {},
            "skill_match": {},
            "gaps": ["Add metrics/impact to experience bullet points"],
            "strengths": [],
            "overall_score": 50.0
        }

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task("Optimizing bullets...", total=None)
            improved = improve_resume(state)

        optimized_bullets = improved.get("ats_optimized_bullets", [])
        
        table = Table(title="STAR Bullet Optimization Results", box=box.ROUNDED)
        table.add_column("Original Bullet", style="dim red", width=40)
        table.add_column("ATS Optimized (STAR)", style="bold green", width=55)

        for orig, opt in zip(existing_bullets, optimized_bullets):
            improved_bullet = opt.get("improved", "") if isinstance(opt, dict) else opt
            table.add_row(orig, improved_bullet)
        
        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Bullet optimization failed:[/] {e}")
        logger.exception("CLI Bullet optimization failed")
        sys.exit(1)


@cli.command()
@click.argument("resume_file", type=click.Path(exists=True))
@click.option("--remote-only", is_flag=True, help="Only search for remote roles")
@click.option("--location", default="", help="Filter jobs by location string")
@click.option("--limit", default=10, help="Maximum job listings to retrieve")
def jobs(resume_file, remote_only, location, limit):
    """Generate search queries and fetch matching jobs for a resume."""
    if not PIPELINE_LOADED:
        console.print(f"[bold red]Error:[/] Pipeline modules failed: {PIPELINE_ERROR}")
        sys.exit(1)

    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task("Parsing resume and generating job queries...", total=None)
            resume_text = read_text_or_pdf(resume_file)
            
            # Simple resume parser call
            from agents.resume_parser import parse_resume
            # Mock graph state wrapper
            mock_state = {"resume_text": resume_text}
            parsed_data = parse_resume(mock_state).get("resume_parsed", {})
            
            # Query generator
            queries_data = generate_search_queries(parsed_data)
            titles = queries_data.get("job_titles", ["Software Engineer"])
            keywords = queries_data.get("search_keywords", ["Python"])
            skills = parsed_data.get("skills", [])
            
            progress.add_task(f"Searching jobs using keywords {keywords[:3]}...", total=None)
            all_jobs = search_jobs(
                queries=keywords + titles,
                location=location,
                remote_only=remote_only,
                max_results=limit * 2
            )
            
            progress.add_task("Scoring and ranking jobs...", total=None)
            scored = score_jobs(
                resume_text=resume_text,
                resume_skills=skills,
                jobs=all_jobs,
                min_score=20.0
            )

        if not scored:
            console.print("[bold yellow]No matching jobs found.[/] Try adjusting location filter or keywords.")
            return

        table = Table(title=f"Matchmaking Dashboard for {parsed_data.get('name', 'Candidate')}", box=box.ROUNDED)
        table.add_column("Score", style="bold cyan")
        table.add_column("Title", style="white")
        table.add_column("Company", style="yellow")
        table.add_column("Location", style="dim green")
        table.add_column("Matched Skills", style="blue")

        for s_job in scored[:limit]:
            # category / color formatting
            score = s_job.match_score
            color = "green" if score >= 75 else "yellow" if score >= 50 else "white"
            matched_str = ", ".join(s_job.matched_skills[:4])
            
            table.add_row(
                f"[{color}]{score:.1f}%[/]",
                s_job.listing.title,
                s_job.listing.company,
                s_job.listing.location,
                matched_str
            )
        
        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Job matchmaking failed:[/] {e}")
        logger.exception("CLI Job finder failed")
        sys.exit(1)


@cli.command("stress-test")
@click.argument("payload")
def stress_test(payload):
    """Scan a text input/payload for prompt injection attacks."""
    if not PIPELINE_LOADED:
        console.print(f"[bold red]Error:[/] Pipeline modules failed: {PIPELINE_ERROR}")
        sys.exit(1)
        
    try:
        is_inj, conf, reason = scan_prompt_injection(payload)
        
        if is_inj:
            console.print(Panel(
                f"[bold red]PROMPT INJECTION DETECTED[/]\n\n"
                f"[bold]Confidence Score:[/] {conf:.2f}\n"
                f"[bold]Analysis Reason:[/] {reason}",
                title="Security Alert",
                border_style="red"
            ))
        else:
            console.print(Panel(
                f"[bold green]INPUT VERIFIED SECURE[/]\n\n"
                f"[bold]Confidence Score:[/] {1-conf:.2f}\n"
                f"[bold]Verdict:[/] Payload does not show prompt injection patterns.",
                title="Security Audit Pass",
                border_style="green"
            ))
            
    except Exception as e:
        console.print(f"[bold red]Scanner failure:[/] {e}")
        sys.exit(1)


@cli.command()
@click.argument("files_pattern")
@click.option("--jd", help="Job description text directly")
@click.option("--jd-file", type=click.Path(exists=True), help="Path to text file containing job description")
def batch(files_pattern, jd, jd_file):
    """Batch-analyze multiple resumes against a job description."""
    if not PIPELINE_LOADED:
        console.print(f"[bold red]Error:[/] Pipeline modules failed: {PIPELINE_ERROR}")
        sys.exit(1)

    # Get files matching pattern
    files = glob.glob(files_pattern)
    if not files:
        console.print(f"[bold red]Error:[/] No files matched pattern '{files_pattern}'")
        sys.exit(1)
        
    jd_content = ""
    if jd:
        jd_content = jd
    elif jd_file:
        with open(jd_file, "r", encoding="utf-8", errors="ignore") as f:
            jd_content = f.read()
    else:
        jd_content = "Software Engineer Developer Python JavaScript Git"
        console.print("[bold yellow]Warning:[/] No JD provided. Using default fallback keywords.")

    table = Table(title="Batch Candidate Leaderboard", box=box.ROUNDED)
    table.add_column("Rank", justify="center")
    table.add_column("Filename", style="cyan")
    table.add_column("Candidate", style="white")
    table.add_column("Match Score", justify="right")
    table.add_column("Status", justify="center")

    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("Processing batch resumes...", total=len(files))
        
        for file in files:
            progress.update(task, description=f"Analyzing {os.path.basename(file)}...")
            try:
                text = read_text_or_pdf(file)
                res = run_analysis(resume_text=text, jd_text=jd_content, pdf_path=file if file.lower().endswith(".pdf") else None, premium_mode=False)
                score = float(res.get("match_score", 0.0))
                name = res.get("resume_parsed", {}).get("name", "N/A")
                results.append((score, file, name))
            except Exception as e:
                results.append((0.0, file, f"Error: {str(e)}"))
            progress.advance(task)

    # Sort results
    results.sort(key=lambda x: x[0], reverse=True)
    
    for idx, (score, file, name) in enumerate(results, start=1):
        color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
        status = "Top" if score >= 75 else "Match" if score >= 50 else "Low"
        table.add_row(
            str(idx),
            os.path.basename(file),
            name,
            f"[{color}]{score:.1f}%[/]",
            status
        )

    console.print("\n")
    console.print(table)


@cli.command()
@click.option("--drift", is_flag=True, help="Display statistical data drift audit")
@click.option("--json-output", is_flag=True, help="Output metrics in raw JSON")
def telemetry(drift, json_output):
    """View database events, processing costs, and statistical drift."""
    if not PIPELINE_LOADED:
        console.print(f"[bold red]Error:[/] Pipeline modules failed: {PIPELINE_ERROR}")
        sys.exit(1)

    if drift:
        try:
            report = DriftMonitor.analyze_drift()
            if json_output:
                click.echo(json.dumps(report, indent=2))
                return
                
            status_colors = {"STABLE": "green", "WARNING": "yellow", "DRIFT DETECTED": "red", "Insufficient Data": "white"}
            status_color = status_colors.get(report.get("status", "STABLE"), "white")
            
            console.print("\n")
            console.print(Panel(
                f"[bold]Overall System Status:[/] [{status_color}]{report.get('status', 'N/A')}[/]\n"
                f"[bold]Population Stability Index (PSI):[/] {report.get('psi_score', 0.0)}\n"
                f"[bold]Analyses in Window:[/] {report.get('run_count_analyzed', 0)}",
                title="Statistical Data Drift Audit Report",
                subtitle="Baseline comparison vs recent 50 runs",
                border_style=status_color
            ))
            
            if "metrics" in report:
                table = Table(title="Drift Metrics Summary", box=box.ROUNDED)
                table.add_column("Metric Channel", style="cyan")
                table.add_column("Baseline Value", justify="right")
                table.add_column("Recent Value (Avg)", justify="right")
                table.add_column("Status", justify="center")
                
                for metric, data in report["metrics"].items():
                    base = data.get("baseline", "N/A")
                    recent = data.get("recent", "N/A")
                    is_warn = data.get("drift_warning", False)
                    m_status = "[bold red]DRIFT[/]" if is_warn else "[green]OK[/]"
                    
                    table.add_row(
                        metric.replace("_", " ").title(),
                        str(base),
                        str(recent),
                        m_status
                    )
                console.print(table)
            else:
                console.print(f"[dim]{report.get('message', 'No message available')}[/]")
                
        except Exception as e:
            console.print(f"[bold red]Drift audit failed:[/] {e}")
            
    else:
        # Standard Telemetry Summary
        try:
            summary = TelemetryLogger.get_summary_metrics()
            logs = TelemetryLogger.get_recent_logs(15)
            
            if json_output:
                click.echo(json.dumps({"summary": summary, "logs": logs}, indent=2))
                return
                
            console.print("\n")
            console.print(Panel(
                f"[bold]Total Pipelines Run:[/] {summary.get('total_runs', 0)}\n"
                f"[bold]Accumulated Cost (USD):[/] ${summary.get('total_cost_usd', 0.0):.6f}\n"
                f"[bold]Average Latency (Sec):[/] {summary.get('average_latency_sec', 0.0):.2f}s",
                title="MLOps Telemetry Overview",
                border_style="cyan"
            ))
            
            # Print recent log events
            if logs:
                table = Table(title="Recent Telemetry Events", box=box.ROUNDED)
                table.add_column("Timestamp", style="dim")
                table.add_column("Node", style="yellow")
                table.add_column("Tokens", justify="right")
                table.add_column("Latency", justify="right")
                table.add_column("Status", justify="center")
                
                for log in logs[:8]:
                    status_col = "green" if log.get("status") == "success" else "red"
                    table.add_row(
                        log.get("timestamp", "")[:19].replace("T", " "),
                        log.get("node_name", "pipeline"),
                        f"{log.get('prompt_tokens',0) + log.get('completion_tokens',0)}",
                        f"{log.get('latency_sec',0.0):.2f}s",
                        f"[{status_col}]{log.get('status')}[/]"
                    )
                console.print(table)
                
        except Exception as e:
            console.print(f"[bold red]Telemetry reading failed:[/] {e}")


@cli.command()
def health():
    """Verify dependencies, SQLite/MongoDB endpoints, and API keys."""
    console.print("\n[bold white]PSI Resume Analyser: Diagnostic System Health Checks[/]\n")
    
    # 1. Check API Keys
    keys = ["GROQ_API_KEY", "GOOGLE_API_KEY", "HF_TOKEN", "HUGGINGFACE_API_KEY"]
    table_keys = Table(title="API Credentials Status", box=box.ROUNDED)
    table_keys.add_column("Credential Name", style="cyan")
    table_keys.add_column("Status", justify="center")
    
    for key in keys:
        val = os.environ.get(key)
        status = "[bold green]FOUND[/]" if val else "[dim yellow]MISSING (FALLBACKS ENABLED)[/]"
        if key == "GOOGLE_API_KEY" and val:
            status = "[bold green]FOUND (PRIMARY GEMINI LLM ACTIVE)[/]"
        table_keys.add_row(key, status)
    console.print(table_keys)

    # 2. Check Package Imports
    packages = {
        "click": "Click (CLI Builder)",
        "rich": "Rich (Terminal UI)",
        "chromadb": "ChromaDB (Vector Store cache)",
        "prometheus_client": "Prometheus Client (Instrumentation)",
        "fastapi": "FastAPI (REST Endpoints)",
        "langgraph": "LangGraph (Agent Graph Router)",
        "pdfplumber": "PDFPlumber (Resume parsing extractor)",
        "email_validator": "Email Validator (Auth schema)"
    }
    
    table_pkg = Table(title="Library Dependencies Health", box=box.ROUNDED)
    table_pkg.add_column("Library Name", style="cyan")
    table_pkg.add_column("Status", justify="center")
    
    for pkg, label in packages.items():
        try:
            __import__(pkg)
            status = "[bold green]OK[/]"
        except ImportError:
            status = "[bold red]NOT INSTALLED[/]"
            if pkg in ["chromadb", "prometheus_client"]:
                status = "[yellow]NOT INSTALLED (RUNNING WITH LOCAL FALLBACKS)[/]"
        table_pkg.add_row(label, status)
    console.print(table_pkg)

    # 3. Check Database Connections
    table_db = Table(title="Databases Connection Status", box=box.ROUNDED)
    table_db.add_column("Database Server", style="cyan")
    table_db.add_column("Connection Status", justify="center")
    
    # Check SQLite
    try:
        from core.db import get_db_connection
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        table_db.add_row("SQLite (Local Cache & Telemetry DB)", "[bold green]CONNECTED[/]")
    except Exception as e:
        table_db.add_row("SQLite (Local Cache & Telemetry DB)", f"[bold red]FAILED ({str(e)})[/]")

    # Check MongoDB
    try:
        from core.mongo_db import get_db
        db = get_db()
        if db is not None:
            table_db.add_row("MongoDB User Memory Store", "[bold green]CONNECTED[/]")
        else:
            table_db.add_row("MongoDB User Memory Store", "[yellow]SKIPPED (URI NOT SET / LOCAL MODE)[/]")
    except Exception as e:
        table_db.add_row("MongoDB User Memory Store", f"[bold red]FAILED ({str(e)})[/]")
        
    console.print(table_db)
    
    console.print("[bold green]Diagnostics Completed.[/]\n")


if __name__ == "__main__":
    cli()
