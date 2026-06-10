"""
Scoring agent node.

Computes keyword, semantic, experience, and education scores and then
produces a weighted overall score together with detailed match breakdowns.
"""

import json
import logging
from typing import Any, Dict, List

from agents import resume_parser
from agents.state import ResumeJDState
from config.prompts import SCORER_PROMPT
from config.settings import settings
from core.similarity import compute_keyword_overlap, compute_semantic_score

logger = logging.getLogger(__name__)

# ── Education-level hierarchy (higher index = higher level) ─────────────────
_EDUCATION_LEVELS: Dict[str, int] = {
    "high school": 1,
    "diploma": 2,
    "associate": 3,
    "bachelor": 4,
    "bachelors": 4,
    "b.sc": 4,
    "b.tech": 4,
    "b.e": 4,
    "bs": 4,
    "ba": 4,
    "master": 5,
    "masters": 5,
    "m.sc": 5,
    "m.tech": 5,
    "ms": 5,
    "ma": 5,
    "mba": 5,
    "phd": 6,
    "ph.d": 6,
    "doctorate": 6,
}


def _degree_level(degree_str: str) -> int:
    """Map a free-text degree string to a numeric level."""
    if not degree_str:
        return 0
    text = degree_str.lower().strip()
    for token, level in _EDUCATION_LEVELS.items():
        if token in text:
            return level
    return 0


def _compute_education_score(resume_parsed: dict, jd_extracted: dict) -> Dict[str, Any]:
    """Compare highest resume degree against JD requirement."""
    education_entries = resume_parsed.get("education") or []
    resume_degrees = [e.get("degree", "") for e in education_entries if e and isinstance(e, dict)]
    resume_max_level = max((_degree_level(d) for d in resume_degrees), default=0)
    resume_best = max(resume_degrees, key=_degree_level, default="Not specified")

    required_degree: str = jd_extracted.get("education_requirement", "") or ""
    required_level = _degree_level(required_degree)

    if required_level == 0:
        score = 100.0
        verdict = "No specific education requirement stated."
    elif resume_max_level >= required_level:
        score = 100.0
        verdict = "Meets or exceeds education requirement."
    elif resume_max_level == required_level - 1:
        score = 60.0
        verdict = "Slightly below education requirement."
    else:
        score = max(30.0, (resume_max_level / max(required_level, 1)) * 100)
        verdict = "Below education requirement."

    return {
        "score": round(score, 1),
        "detail": {
            "resume_degree": resume_best,
            "required_degree": required_degree or "Not specified",
            "verdict": verdict,
        },
    }


def _compute_experience_score_llm(
    resume_parsed: dict,
    jd_extracted: dict,
) -> Dict[str, Any]:
    """Use the LLM for a nuanced experience comparison.

    Falls back to a simple numeric comparison if the LLM is unavailable.
    """
    res_years_val = resume_parsed.get("total_experience_years", 0)
    resume_years: float = float(res_years_val) if res_years_val is not None else 0.0

    req_years_val = jd_extracted.get("min_experience_years", 0)
    required_years: float = float(req_years_val) if req_years_val is not None else 0.0

    # Quick path: if no experience required, full marks
    if required_years <= 0:
        return {
            "score": 100.0,
            "detail": {
                "resume_years": resume_years,
                "required_years": required_years,
                "verdict": "No minimum experience requirement.",
            },
        }

    try:
        llm, _ = resume_parser.get_llm()
        prompt = (
            f"{SCORER_PROMPT}\n\n"
            f"## Inputs\n"
            f"Resume Experience: {json.dumps(resume_parsed.get('experience') or [], default=str)}\n"
            f"Resume Total Experience Years: {resume_years}\n"
            f"JD Required Experience Years: {required_years}\n"
            f"JD Responsibilities: {json.dumps(jd_extracted.get('responsibilities') or [], default=str)}"
        )
        response = llm.invoke(prompt)
        data = resume_parser._extract_json(response.content)  # type: ignore[union-attr]
        exp_score_val = data.get("experience_score", 0)
        score = float(exp_score_val) if exp_score_val is not None else 0.0
        verdict = data.get("verdict", "")
        return {
            "score": min(max(round(score, 1), 0), 100),
            "detail": {
                "resume_years": resume_years,
                "required_years": required_years,
                "verdict": verdict,
            },
        }
    except Exception as exc:
        logger.warning("LLM experience scoring failed (%s); using numeric fallback.", exc)

    # Numeric fallback
    if resume_years >= required_years:
        score = 100.0
        verdict = "Meets experience requirement."
    else:
        ratio = resume_years / required_years
        score = round(ratio * 100, 1)
        verdict = f"Has {resume_years} of {required_years} required years."

    return {
        "score": min(max(score, 0), 100),
        "detail": {
            "resume_years": resume_years,
            "required_years": required_years,
            "verdict": verdict,
        },
    }


def _identify_strengths_and_gaps(
    matched: List[str],
    missing: List[str],
    experience_detail: dict,
    education_detail: dict,
) -> tuple:
    """Build human-readable strengths and gaps lists."""
    strengths: List[str] = []
    gaps: List[str] = []

    if matched:
        strengths.append(f"Matches {len(matched)} key skills: {', '.join(matched[:10])}")
    if experience_detail.get("verdict", "").lower().startswith("meets"):
        strengths.append("Experience level meets or exceeds the requirement.")
    if education_detail.get("verdict", "").lower().startswith("meets"):
        strengths.append("Education level meets or exceeds the requirement.")

    if missing:
        gaps.append(f"Missing {len(missing)} required skills: {', '.join(missing[:10])}")
    if experience_detail.get("resume_years", 0) < experience_detail.get("required_years", 0):
        gaps.append(
            f"Experience gap: {experience_detail['resume_years']} vs "
            f"{experience_detail['required_years']} required years."
        )
    if education_detail.get("verdict", "").lower().startswith("below"):
        gaps.append(f"Education gap: {education_detail.get('verdict', '')}")

    return strengths, gaps


# ── Agent node ──────────────────────────────────────────────────────────────

def score_match(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: compute all match scores and detailed breakdowns.

    Reads normalized skills, parsed resume, and extracted JD. Writes all
    ``*_score``, ``*_match``, ``strengths``, and ``gaps`` keys.
    """
    resume_skills: List[str] = state.get("resume_skills_normalized", [])
    jd_skills: List[str] = state.get("jd_skills_normalized", [])
    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})

    # ── Keyword overlap ──────────────────────────────────────────────────
    keyword_result = compute_keyword_overlap(resume_skills, jd_skills)
    keyword_score: float = keyword_result.get("score", 0.0)
    matched_skills: List[str] = keyword_result.get("matched", [])
    missing_skills: List[str] = keyword_result.get("missing", [])
    overlap_pct: float = keyword_result.get("overlap_pct", 0.0)

    # ── Semantic similarity ──────────────────────────────────────────────
    resume_text: str = state.get("resume_text", "")
    jd_text: str = state.get("jd_text", "")
    semantic_score: float = compute_semantic_score(resume_text, jd_text)

    # ── Experience ───────────────────────────────────────────────────────
    exp_result = _compute_experience_score_llm(resume_parsed, jd_extracted)
    experience_score: float = exp_result["score"]

    # ── Education ────────────────────────────────────────────────────────
    edu_result = _compute_education_score(resume_parsed, jd_extracted)
    education_score: float = edu_result["score"]

    # ── Weighted overall ─────────────────────────────────────────────────
    weights = getattr(settings, "scoring", None)
    w_kw = getattr(weights, "keyword_match", 0.40) if weights else 0.40
    w_sem = getattr(weights, "semantic_similarity", 0.25) if weights else 0.25
    w_exp = getattr(weights, "experience_relevance", 0.25) if weights else 0.25
    w_edu = getattr(weights, "education_match", 0.10) if weights else 0.10

    overall_score = round(
        w_kw * keyword_score
        + w_sem * semantic_score
        + w_exp * experience_score
        + w_edu * education_score,
        1,
    )

    # ── Strengths & gaps ─────────────────────────────────────────────────
    strengths, gaps = _identify_strengths_and_gaps(
        matched_skills,
        missing_skills,
        exp_result["detail"],
        edu_result["detail"],
    )

    logger.info(
        "Scores — keyword: %.1f, semantic: %.1f, experience: %.1f, "
        "education: %.1f, overall: %.1f",
        keyword_score,
        semantic_score,
        experience_score,
        education_score,
        overall_score,
    )

    return {
        "keyword_score": keyword_score,
        "semantic_score": semantic_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "overall_score": overall_score,
        "skill_match": {
            "matched": matched_skills,
            "missing": missing_skills,
            "overlap_pct": overlap_pct,
        },
        "experience_match": exp_result["detail"],
        "education_match": edu_result["detail"],
        "strengths": strengths,
        "gaps": gaps,
    }

# refactor: use resume_parser module level imports for mock testing compatibility
