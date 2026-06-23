"""
Candidate Digital Twin and Recruiter Digital Twin Simulator.
Predicts job family alignment, interview risk metrics, recruiter objections,
and generates personalized prep roadmaps based on resume contents.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class CandidateDigitalTwin:
    """
    Candidate Twin representing capabilities, preferences, interview risks, and study paths.
    """

    @staticmethod
    def construct_twin(resume_parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes parsed resume to build the candidate digital twin profile."""
        name = resume_parsed.get("name", "Candidate")
        skills = [s.lower() for s in resume_parsed.get("skills", [])]
        experience = resume_parsed.get("experience", [])

        # 1. Predict target job families
        job_families = []
        if any(s in skills for s in ["pytorch", "tensorflow", "scikit-learn", "keras", "machine learning", "mlops"]):
            job_families.append({"family": "AI / Machine Learning Engineering", "confidence": 0.95})
        if any(s in skills for s in ["django", "fastapi", "flask", "node.js", "express", "backend", "python", "java"]):
            job_families.append({"family": "Backend Software Engineering", "confidence": 0.90})
        if any(s in skills for s in ["react", "vue", "angular", "html", "css", "javascript", "typescript", "frontend"]):
            job_families.append({"family": "Frontend / Web Development", "confidence": 0.85})
        if any(s in skills for s in ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "devops"]):
            job_families.append({"family": "Cloud Systems & DevOps Engineering", "confidence": 0.88})
        
        if not job_families:
            job_families.append({"family": "General Software Development", "confidence": 0.70})

        # 2. Risk Estimation Heuristics
        risks = []
        total_jobs = len(experience)
        if total_jobs == 0:
            risks.append({"area": "Professional Experience", "description": "No formal industry experience parsed; high risk for senior/staff roles.", "severity": "High"})
        elif total_jobs == 1:
            risks.append({"area": "Experience Breadth", "description": "Single-employer tenure might trigger concern over adaptability to different architectures.", "severity": "Low"})

        # Check for gap metrics (bullets without numeric impact)
        non_metric_bullets = 0
        total_bullets = 0
        for job in experience:
            for bullet in job.get("bullets", []):
                total_bullets += 1
                if not any(char.isdigit() for char in bullet):
                    non_metric_bullets += 1
        
        if total_bullets > 0 and (non_metric_bullets / total_bullets) > 0.6:
            risks.append({"area": "Impact Quantification", "description": "High percentage of descriptive bullets without measurable results or metrics.", "severity": "Medium"})

        # Missing deployment checks
        if not any(s in skills for s in ["docker", "kubernetes", "aws", "gcp", "terraform", "cicd"]):
            risks.append({"area": "Production Maturity", "description": "No containerization or cloud deployment tools listed. Risk for DevOps/SaaS environments.", "severity": "Medium"})

        # Calculate overall risk percentage
        risk_score = 15.0 # baseline
        for r in risks:
            if r["severity"] == "High":
                risk_score += 30.0
            elif r["severity"] == "Medium":
                risk_score += 15.0
            else:
                risk_score += 5.0
        risk_score = min(risk_score, 100.0)

        # 3. Personalized Study Roadmap
        roadmap = []
        if "python" in skills and "fastapi" not in skills:
            roadmap.append({"topic": "API Design with FastAPI", "resource": "FastAPI Tutorial User Guide", "time_estimate": "10 hours"})
        if not any(s in skills for s in ["docker", "kubernetes"]):
            roadmap.append({"topic": "Containerization Fundamentals", "resource": "Docker Deep Dive (Docker Docs)", "time_estimate": "15 hours"})
        if "pytorch" in skills and "mlops" not in skills:
            roadmap.append({"topic": "ML Model Registry & Tracking", "resource": "MLflow & LangSmith Guides", "time_estimate": "12 hours"})
        
        # Fallback items to guarantee roadmap richness
        roadmap.append({"topic": "System Design & Scalability Patterns", "resource": "Designing Data-Intensive Applications", "time_estimate": "25 hours"})
        roadmap.append({"topic": "Agentic Orchestration Frameworks", "resource": "LangGraph Stateful Agents tutorials", "time_estimate": "8 hours"})

        return {
            "candidate_name": name,
            "job_families": job_families,
            "compensation_band": CandidateDigitalTwin._estimate_compensation(skills, total_jobs),
            "interview_risk_score": risk_score,
            "risk_mitigation_plan": risks,
            "study_roadmap": roadmap
        }

    @staticmethod
    def _estimate_compensation(skills: List[str], total_jobs: int) -> str:
        """Heuristic salary band estimator based on skillset premium and seniority."""
        base = 80000
        premium_skills = ["pytorch", "mlops", "langgraph", "kubernetes", "go", "scala", "system design"]
        
        skill_bonus = sum(3500 for s in skills if s in premium_skills)
        tenure_bonus = min(total_jobs * 8000, 45000)
        
        low_bound = base + skill_bonus + tenure_bonus
        high_bound = int(low_bound * 1.35)
        
        return f"${low_bound // 1000}k - ${high_bound // 1000}k USD"


class RecruiterDigitalTwin:
    """
    Recruiter Twin simulating objections, screen filters, and line-item attention dynamics.
    """

    @staticmethod
    def simulate_screening(resume_parsed: Dict[str, Any], jd_text: str) -> Dict[str, Any]:
        """Simulates how a recruiter reviews the resume against a job description."""
        skills = [s.lower() for s in resume_parsed.get("skills", [])]
        experience = resume_parsed.get("experience", [])

        # 1. Screen Filter Checks (Objections)
        objections = []
        
        # JD Keyword checklist
        jd_lower = jd_text.lower()
        must_haves = ["python", "react", "kubernetes", "docker", "sql", "aws", "pytorch"]
        missing_must_haves = [kw for kw in must_haves if kw in jd_lower and kw not in skills]
        
        for m in missing_must_haves:
            objections.append({
                "type": "Missing Core Tech Stack",
                "detail": f"Job description lists {m.capitalize()}, but it is absent from candidate skills list.",
                "severity": "High"
            })

        # Education checks
        if "degree" in jd_lower or "b.s." in jd_lower or "computer science" in jd_lower:
            edu = resume_parsed.get("education", [])
            has_cs = False
            for school in edu:
                degree_text = school.get("degree", "").lower()
                if "computer" in degree_text or "engineering" in degree_text or "science" in degree_text or "technology" in degree_text:
                    has_cs = True
            if not has_cs and len(edu) > 0:
                objections.append({
                    "type": "Non-Traditional Background",
                    "detail": "Academic degrees do not explicitly mention Computer Science or STEM disciplines.",
                    "severity": "Low"
                })

        if not objections:
            objections.append({
                "type": "None",
                "detail": "Candidate meets all immediate screening criteria.",
                "severity": "None"
            })

        # 2. Line Item Heatmap Attention Predictions
        attention_map = []
        for job in experience:
            bullets = job.get("bullets", [])
            
            for b in bullets:
                # Obvious positive signals (numeric achievements, active lead verbs)
                score = 50 # neutral baseline
                triggers = []
                
                if any(char.isdigit() for char in b):
                    score += 25
                    triggers.append("quantifiable metric")
                if any(verb in b.lower() for verb in ["led", "spearheaded", "architected", "optimized", "designed", "implemented"]):
                    score += 15
                    triggers.append("strong action verb")
                if any(tech in b.lower() for tech in MustHaveKeywords.TECH_STACK):
                    score += 10
                    triggers.append("relevant tech stack")
                
                # Negative or weak lines
                if len(b) < 30:
                    score -= 20
                    triggers.append("insufficient details")
                if any(weak in b.lower() for weak in ["responsible for", "helped", "assisted", "duties included"]):
                    score -= 15
                    triggers.append("passive responsibilities phrasing")

                score = max(0, min(100, score))
                attention_map.append({
                    "text": b,
                    "attention_percentage": score,
                    "triggers": triggers
                })

        # 3. Simulated Interview Script
        interview_questions = []
        if "pytorch" in skills:
            interview_questions.append({
                "question": "Can you describe a machine learning pipeline you trained in PyTorch, highlighting the model checkpointing and distributed training strategies you used?",
                "intended_to_test": "In-depth PyTorch scaling knowledge versus keyword usage."
            })
        if "kubernetes" in skills or "docker" in skills:
            interview_questions.append({
                "question": "How did you manage configmaps, secrets, and volume mounts when migrating services to your Kubernetes cluster?",
                "intended_to_test": "Infrastructure operational maturity."
            })
        
        # General question fallback
        interview_questions.append({
            "question": "Walk me through the system design of your most complex project. What architectural bottlenecks did you encounter, and how did you resolve them?",
            "intended_to_test": "System design leadership and trade-off analysis."
        })

        return {
            "objections_raised": objections,
            "attention_heatmap": attention_map[:8],
            "screening_questions": interview_questions
        }


class MustHaveKeywords:
    TECH_STACK = {
        "python", "javascript", "typescript", "go", "rust", "cpp",
        "react", "angular", "vue", "next.js", "fastapi", "django",
        "aws", "gcp", "azure", "kubernetes", "docker", "terraform",
        "postgresql", "mongodb", "redis", "elasticsearch", "kafka",
        "pytorch", "tensorflow", "scikit-learn", "langchain", "langgraph"
    }
