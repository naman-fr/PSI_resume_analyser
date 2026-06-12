"""
Skill-normalizer agent node.

Normalizes raw skill strings from both the resume and JD into canonical
forms using a taxonomy-first approach with LLM fallback.
"""

import json
import logging
import re
from typing import Any, Dict, List

from agents import resume_parser
from agents.state import ResumeJDState
from config.prompts import SKILL_NORMALIZER_PROMPT
from core.skill_taxonomy import SkillTaxonomy

logger = logging.getLogger(__name__)


def _normalize_skill_list(
    raw_skills: List[str],
    taxonomy: SkillTaxonomy,
) -> List[str]:
    """Normalize a list of skills using the taxonomy lookup.

    Returns a deduplicated list of canonical skill names.  Skills that the
    taxonomy cannot resolve are collected and returned as-is (the caller can
    optionally run them through the LLM).
    """
    normalized: List[str] = []
    unresolved: List[str] = []

    for skill in raw_skills:
        canonical = taxonomy.normalize(skill)
        if canonical:
            normalized.append(canonical)
        else:
            unresolved.append(skill)

    return normalized, unresolved  # type: ignore[return-value]


def _llm_normalize_mapping(skills: List[str]) -> Dict[str, str]:
    """Use the LLM to normalize a list of unresolved skill strings.

    Returns a mapping of original_skill -> canonical_form.
    """
    if not skills:
        return {}

    try:
        llm, _ = resume_parser.get_llm()
        prompt = f"{SKILL_NORMALIZER_PROMPT}\n\n## Input Skills\n{json.dumps(skills)}"
        response = llm.invoke(prompt)
        raw: str = response.content  # type: ignore[union-attr]

        data = resume_parser._extract_json(raw)
        mapping = {}
        if isinstance(data, dict):
            if "mapping" in data and isinstance(data["mapping"], dict):
                mapping = {str(k): str(v) for k, v in data["mapping"].items()}
            
            if not mapping:
                norm_list = data.get("normalized_skills") or data.get("skills") or []
                if isinstance(norm_list, list) and len(norm_list) == len(skills):
                    mapping = {skills[i]: str(norm_list[i]) for i in range(len(skills))}
        elif isinstance(data, list) and len(data) == len(skills):
            mapping = {skills[i]: str(data[i]) for i in range(len(skills))}
            
        return mapping
    except Exception as exc:
        logger.warning("LLM skill normalization failed (%s); keeping originals.", exc)
        err_msg = str(exc).lower()
        if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
            raise exc
        return {}


def normalize_skills(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: normalize skills from both resume and JD.

    Reads ``resume_parsed`` and ``jd_extracted``, produces
    ``resume_skills_normalized`` and ``jd_skills_normalized``.
    """
    if state.get("error"):
        return {}

    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})

    taxonomy = SkillTaxonomy()

    # ── Resume skills ────────────────────────────────────────────────────
    raw_resume_skills: List[str] = resume_parsed.get("skills") or []
    resume_norm, resume_unresolved = _normalize_skill_list(raw_resume_skills, taxonomy)

    # ── JD skills ────────────────────────────────────────────────────────
    raw_jd_skills: List[str] = (
        (jd_extracted.get("required_skills") or [])
        + (jd_extracted.get("preferred_skills") or [])
    )
    jd_norm, jd_unresolved = _normalize_skill_list(raw_jd_skills, taxonomy)

    # Combine all unresolved skills to perform a single LLM call
    combined_unresolved = list(set(resume_unresolved + jd_unresolved))
    if combined_unresolved:
        try:
            mapping = _llm_normalize_mapping(combined_unresolved)
        except Exception as exc:
            err_msg = str(exc).lower()
            if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
                return {"error": "API Quota Exhausted: Groq/Gemini rate limit exceeded. Please wait 1-2 minutes and try again."}
            logger.exception("Skill normalization LLM call failed.")
            mapping = {}
        
        # Map resume unresolved skills
        for skill in resume_unresolved:
            canonical = mapping.get(skill) or skill
            if canonical:
                resume_norm.append(canonical)
                
        # Map JD unresolved skills
        for skill in jd_unresolved:
            canonical = mapping.get(skill) or skill
            if canonical:
                jd_norm.append(canonical)

    # Deduplicate while preserving order
    resume_skills_final = list(dict.fromkeys(s.lower() for s in resume_norm))
    jd_skills_final = list(dict.fromkeys(s.lower() for s in jd_norm))

    logger.info(
        "Skills normalized — resume: %d, JD: %d.",
        len(resume_skills_final),
        len(jd_skills_final),
    )
    return {
        "resume_skills_normalized": resume_skills_final,
        "jd_skills_normalized": jd_skills_final,
    }

# refactor: import resume_parser module for robust mock tests validation
