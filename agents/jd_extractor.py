"""
Job-description extractor agent node.

Extracts structured requirements from raw job-description text using an LLM.
"""

import json
import logging
import re
from typing import Any, Dict

from agents import resume_parser
from agents.state import ResumeJDState
from config.prompts import JD_EXTRACTOR_PROMPT

logger = logging.getLogger(__name__)


def extract_jd(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: extract structured data from ``jd_text``.

    Sets ``jd_extracted`` with the following schema::

        {
            "job_title": str,
            "company": str,
            "required_skills": [str, ...],
            "preferred_skills": [str, ...],
            "min_experience_years": float,
            "education_requirement": str,
            "responsibilities": [str, ...],
            "certifications_required": [str, ...]
        }
    """
    if state.get("error"):
        return {}

    jd_text: str = state.get("jd_text", "")
    if not jd_text.strip():
        return {"error": "jd_text is empty — nothing to extract."}

    try:
        llm, provider = resume_parser.get_llm()

        prompt = f"{JD_EXTRACTOR_PROMPT}\n\n## Input Job Description\n{jd_text}"
        response = llm.invoke(prompt)
        raw_content: str = response.content  # type: ignore[union-attr]

        extracted: dict = resume_parser._extract_json(raw_content)

        # Ensure expected keys exist with sensible defaults
        defaults = {
            "job_title": "",
            "company": "",
            "required_skills": [],
            "preferred_skills": [],
            "min_experience_years": 0,
            "education_requirement": "",
            "responsibilities": [],
            "certifications_required": [],
        }
        for key, default in defaults.items():
            extracted.setdefault(key, default)

        logger.info("JD extracted successfully via %s.", provider)
        return {
            "jd_extracted": extracted,
            "provider_used": provider,
        }

    except Exception as exc:
        logger.exception("JD extraction failed.")
        err_msg = str(exc).lower()
        if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
            return {"error": "API Quota Exhausted: Groq/Gemini rate limit exceeded. Please wait 1-2 minutes and try again."}
        return {"error": f"JD extraction failed: {exc}"}

# refactor: import resume_parser module instead of function to support mock testing
