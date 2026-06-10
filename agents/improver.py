"""
Resume-improvement agent node.

Generates actionable improvement suggestions and ATS-optimized resume
bullets based on the gap analysis from the scoring step.
"""

import json
import logging
from typing import Any, Dict, List

from agents import resume_parser
from agents.state import ResumeJDState
from config.prompts import IMPROVER_PROMPT

logger = logging.getLogger(__name__)


def improve_resume(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: generate improvement suggestions and rewritten bullets.

    Reads ``gaps``, ``skill_match``, ``resume_parsed``, ``jd_extracted``, and
    score fields.  Writes ``improvement_suggestions`` and
    ``ats_optimized_bullets``.
    """
    gaps: List[str] = state.get("gaps", [])
    skill_match: dict = state.get("skill_match", {})
    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})
    overall_score: float = state.get("overall_score", 0.0)
    strengths: List[str] = state.get("strengths", [])

    missing_skills: List[str] = skill_match.get("missing", [])

    # Collect existing resume bullets for rewriting
    experience_entries: list = resume_parsed.get("experience", [])
    existing_bullets: List[str] = []
    for entry in experience_entries:
        existing_bullets.extend(entry.get("bullets", []))

    try:
        llm, provider = resume_parser.get_llm()

        prompt = (
            f"{IMPROVER_PROMPT}\n\n"
            f"## Inputs\n"
            f"Job Title: {jd_extracted.get('job_title', 'the target role')}\n"
            f"Current Overall ATS Score: {overall_score}\n"
            f"Candidate Gaps: {json.dumps(gaps, default=str)}\n"
            f"Missing Skills: {json.dumps(missing_skills, default=str)}\n"
            f"Candidate Strengths: {json.dumps(strengths, default=str)}\n"
            f"Existing Resume Bullets: {json.dumps(existing_bullets[:15], default=str)}\n"
            f"JD Required Skills: {json.dumps(jd_extracted.get('required_skills', []), default=str)}\n"
            f"JD Responsibilities: {json.dumps(jd_extracted.get('responsibilities', []), default=str)}"
        )
        response = llm.invoke(prompt)
        raw_content: str = response.content  # type: ignore[union-attr]

        data: dict = resume_parser._extract_json(raw_content)

        suggestions: List[str] = data.get("improvement_suggestions", [])
        optimized_bullets: List[str] = data.get("ats_optimized_bullets", [])

        # Ensure we always have lists
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]
        if not isinstance(optimized_bullets, list):
            optimized_bullets = [str(optimized_bullets)]

        logger.info(
            "Improvement node produced %d suggestions and %d optimized bullets.",
            len(suggestions),
            len(optimized_bullets),
        )
        return {
            "improvement_suggestions": suggestions,
            "ats_optimized_bullets": optimized_bullets,
        }

    except Exception as exc:
        logger.exception("Improvement generation failed.")
        return {
            "improvement_suggestions": [
                "Unable to generate suggestions automatically. "
                "Review the gaps list and incorporate missing skills."
            ],
            "ats_optimized_bullets": [],
            "error": f"Improvement generation failed: {exc}",
        }

# refactor: import resume_parser module to fix mock scope issues in tests
