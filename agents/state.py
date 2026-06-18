"""
LangGraph shared state definition for the resume-analysis pipeline.

Every agent node reads from and writes to this single TypedDict.  Fields use
``total=False`` so each node only needs to return the keys it actually
updates — LangGraph merges partial dicts automatically.
"""

from typing import Any, Optional, TypedDict


class ResumeJDState(TypedDict, total=False):
    """Shared state that flows through every node in the analysis graph."""

    # ── Inputs ───────────────────────────────────────────────────────────
    resume_text: str        # Raw text extracted from the uploaded PDF
    jd_text: str            # Raw job-description text entered by the user

    # ── Parsed data ──────────────────────────────────────────────────────
    resume_parsed: dict     # Structured resume data (name, skills, experience …)
    jd_extracted: dict      # Structured JD requirements

    # ── Normalized skills ────────────────────────────────────────────────
    resume_skills_normalized: list   # Canonical skill names from the resume
    jd_skills_normalized: list       # Canonical skill names from the JD

    # ── Scores (0-100) ───────────────────────────────────────────────────
    keyword_score: float      # Keyword-overlap score
    semantic_score: float     # Embedding-based semantic similarity score
    experience_score: float   # Experience-level match score
    education_score: float    # Education-level match score
    overall_score: float      # Weighted composite score
    recency_score: float      # Skill recency score (0-100)
    achievement_score: float  # Achievement quality score (0-100)
    match_score: float        # Final enterprise-grade ATS score (0-100)

    # ── Industrial Analysis ──────────────────────────────────────────────
    disqualified: bool               # Auto-disqualification flag
    disqualification_reason: str     # Reason for auto-disqualification
    job_hopping_info: dict           # {is_job_hopper, tenure_count, penalty}
    skills_validation: dict          # {validation_ratio, unsupported_skills, penalty}
    red_flags: list                  # Detected red flags list with penalties
    green_flags: list                # Detected green flags list with bonuses
    component_scores: dict           # Breakdowns of all individual factors
    skill_match: dict         # {matched, missing, overlap_pct}
    experience_match: dict    # {resume_years, required_years, verdict}
    education_match: dict     # {resume_degree, required_degree, verdict}
    strengths: list           # Candidate strengths (list of strings)
    gaps: list                # Candidate gaps / weaknesses

    # ── Improvement suggestions ──────────────────────────────────────────
    improvement_suggestions: list   # Actionable improvement advice
    ats_optimized_bullets: list     # Rewritten resume bullets for ATS

    # ── MLOps & Planner ──────────────────────────────────────────────────
    planner_plan: dict              # Orchestration plan containing steps and versions
    critic_report: dict             # Critic evaluation report (validity, confidence, feedback)
    evaluation_logs: dict           # Benchmark results (hallucination rate, conformity)
    loop_count: int                 # Self-reflection loop index counter

    # ── Meta ─────────────────────────────────────────────────────────────
    error: Optional[str]      # Error message (``None`` when everything is OK)
    provider_used: str        # LLM provider that was actually used (e.g. "gemini")

    # ── Premium Verified Tier ────────────────────────────────────────────
    premium_mode: bool               # Enable premium verification features
    invisible_text_flagged: bool     # True if white-on-white text detected
    invisible_text_details: dict     # {detected_words, penalty}
    links_verification: dict         # {trust_score, logs, checked_urls}

# docs: document ResumeJDState fields in detail
