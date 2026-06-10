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


def _llm_normalize(skills: List[str]) -> List[str]:
    """Use the LLM to normalize skills the taxonomy could not resolve.

    Asks the LLM to map each raw skill string to its most common canonical
    name or to confirm it as-is.
    """
    if not skills:
        return []

    try:
        llm, _ = resume_parser.get_llm()
        prompt = f"{SKILL_NORMALIZER_PROMPT}\n\n## Input Skills\n{json.dumps(skills)}"
        response = llm.invoke(prompt)
        raw: str = response.content  # type: ignore[union-attr]

        data = resume_parser._extract_json(raw)
        if isinstance(data, list):
            return [str(s) for s in data]
        if isinstance(data, dict) and "skills" in data:
            return [str(s) for s in data["skills"]]
        return skills  # fallback: return originals
    except Exception as exc:
        logger.warning("LLM skill normalization failed (%s); keeping originals.", exc)
        return skills


def normalize_skills(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: normalize skills from both resume and JD.

    Reads ``resume_parsed`` and ``jd_extracted``, produces
    ``resume_skills_normalized`` and ``jd_skills_normalized``.
    """
    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})

    taxonomy = SkillTaxonomy()

    # ── Resume skills ────────────────────────────────────────────────────
    raw_resume_skills: List[str] = resume_parsed.get("skills") or []
    resume_norm, resume_unresolved = _normalize_skill_list(raw_resume_skills, taxonomy)
    if resume_unresolved:
        llm_resolved = _llm_normalize(resume_unresolved)
        resume_norm.extend(llm_resolved)

    # ── JD skills ────────────────────────────────────────────────────────
    raw_jd_skills: List[str] = (
        (jd_extracted.get("required_skills") or [])
        + (jd_extracted.get("preferred_skills") or [])
    )
    jd_norm, jd_unresolved = _normalize_skill_list(raw_jd_skills, taxonomy)
    if jd_unresolved:
        llm_resolved = _llm_normalize(jd_unresolved)
        jd_norm.extend(llm_resolved)

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
