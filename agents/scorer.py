"""
Scoring agent node.

Computes keyword, semantic, experience, and education scores and then
produces a weighted overall score together with detailed match breakdowns.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agents import resume_parser
from agents.state import ResumeJDState
from config.prompts import SCORER_PROMPT
from config.settings import settings
from core.similarity import compute_keyword_overlap, compute_semantic_score

logger = logging.getLogger(__name__)


def _parse_date_to_months(date_str: str) -> Optional[int]:
    if not date_str or not isinstance(date_str, str):
        return None
    text = date_str.lower().strip()
    if "present" in text or "current" in text or "now" in text:
        return 2026 * 12 + 5 # Assume May 2026
    
    # Try to find year
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if not year_match:
        return None
    year = int(year_match.group(1))
    
    # Try to find month
    month = 6 # Default to June if month not found
    months_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    for mname, mval in months_map.items():
        if mname in text:
            month = mval
            break
    return year * 12 + month


def _calculate_tenure_months(start_str: str, end_str: str) -> int:
    start_m = _parse_date_to_months(start_str)
    end_m = _parse_date_to_months(end_str)
    if start_m is None or end_m is None:
        return 12 # Default to 1 year if unclear
    return max(1, end_m - start_m)


def _calculate_skill_recency_score(resume_parsed: dict, jd_skills: List[str]) -> float:
    if not jd_skills:
        return 100.0

    experience_entries = resume_parsed.get("experience") or []
    recency_sum = 0.0

    for skill in jd_skills:
        skill_lower = skill.lower()
        last_used_year = None
        
        # Check projects
        for proj in resume_parsed.get("projects") or []:
            if isinstance(proj, dict):
                proj_desc = str(proj.get("description", "")).lower()
                proj_tech = [str(t).lower() for t in proj.get("technologies") or []]
                if skill_lower in proj_desc or skill_lower in proj_tech:
                    last_used_year = 2026
        
        # Check work experience
        for entry in experience_entries:
            if not isinstance(entry, dict):
                continue
            role = str(entry.get("role", "")).lower()
            company = str(entry.get("company", "")).lower()
            bullets = [str(b).lower() for b in entry.get("bullets") or []]
            bullets_text = " ".join(bullets)
            
            if skill_lower in role or skill_lower in company or skill_lower in bullets_text:
                end_str = entry.get("end_date") or "Present"
                end_m = _parse_date_to_months(end_str)
                end_year = (end_m // 12) if end_m else 2026
                if last_used_year is None or end_year > last_used_year:
                    last_used_year = end_year
        
        is_in_skills_list = any(skill_lower == s.lower() for s in (resume_parsed.get("skills") or []))
        
        if last_used_year is not None:
            years_ago = 2026 - last_used_year
            if years_ago <= 2:
                recency_sum += 2.0
            elif years_ago <= 5:
                recency_sum += 1.0
            else:
                recency_sum += 0.5
        elif is_in_skills_list:
            recency_sum += 0.2
        else:
            recency_sum += 0.0
            
    max_possible = len(jd_skills) * 2.0
    return round((recency_sum / max_possible) * 100.0, 1) if max_possible > 0 else 100.0


def _calculate_achievement_quality(resume_parsed: dict) -> float:
    experience_entries = resume_parsed.get("experience") or []
    resume_bullets = []
    for entry in experience_entries:
        if isinstance(entry, dict):
            resume_bullets.extend(entry.get("bullets") or [])
            
    if not resume_bullets:
        return 0.0
        
    quality_score = 0
    action_pattern = re.compile(
        r'\b(led|built|designed|implemented|optimized|developed|engineered|created|managed|delivered|reduced|increased|saved)\b', 
        re.IGNORECASE
    )
    context_pattern = re.compile(r'\b(in|at|for|while|across|throughout|using|with)\b', re.IGNORECASE)
    outcome_pattern = re.compile(
        r'\b(increased|decreased|improved|reduced|optimized|maximized|minimized|resulting|achieving|driving|enhanced)\b', 
        re.IGNORECASE
    )
    evidence_pattern = re.compile(r'(\d+[%$\w]|\b\d+\s*(percent|dollars|hours|users|records|days|weeks|months|years|x)\b)', re.IGNORECASE)
    
    for bullet in resume_bullets:
        bullet_str = str(bullet)
        has_action = bool(action_pattern.search(bullet_str))
        has_context = bool(context_pattern.search(bullet_str))
        has_outcome = bool(outcome_pattern.search(bullet_str))
        has_evidence = bool(evidence_pattern.search(bullet_str))
        
        if has_action and has_context and has_outcome and has_evidence:
            quality_score += 10
        elif has_action and has_outcome and has_evidence:
            quality_score += 7
        elif has_action and has_outcome:
            quality_score += 4
        else:
            quality_score += 1
            
    max_possible = len(resume_bullets) * 10
    return round((quality_score / max_possible) * 100.0, 1) if max_possible > 0 else 0.0


def _detect_job_hopping(resume_parsed: dict) -> dict:
    experience_entries = resume_parsed.get("experience") or []
    short_tenures = 0
    
    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue
        start_date = entry.get("start_date") or ""
        end_date = entry.get("end_date") or ""
        tenure_months = _calculate_tenure_months(start_date, end_date)
        
        if tenure_months < 12:
            dep_reason = str(entry.get("departure_reason") or "").lower()
            role = str(entry.get("role") or "").lower()
            company = str(entry.get("company") or "").lower()
            
            has_legit_reason = any(
                kw in dep_reason or kw in role or kw in company
                for kw in ['contract', 'acquisition', 'closure', 'relocation', 'project', 'intern', 'temporary']
            )
            if not has_legit_reason:
                short_tenures += 1
                
    is_job_hopper = short_tenures >= 3
    penalty = -10.0 if is_job_hopper else 0.0
    return {
        "is_job_hopper": is_job_hopper,
        "short_tenure_count": short_tenures,
        "penalty": penalty
    }


def _validate_skills_against_experience(resume_parsed: dict) -> dict:
    skills = resume_parsed.get("skills") or []
    if not skills:
        return {"validation_ratio": 1.0, "unsupported_skills": [], "penalty": 0.0}
        
    experience_entries = resume_parsed.get("experience") or []
    projects = resume_parsed.get("projects") or []
    
    validated_count = 0
    unsupported_skills = []
    
    for skill in skills:
        skill_lower = skill.lower()
        used = False
        
        for entry in experience_entries:
            if not isinstance(entry, dict):
                continue
            desc = " ".join([str(b) for b in entry.get("bullets") or []]) + " " + str(entry.get("role", ""))
            if skill_lower in desc.lower():
                used = True
                break
                
        if not used:
            for proj in projects:
                if not isinstance(proj, dict):
                    continue
                proj_desc = str(proj.get("description", "")) + " " + " ".join([str(t) for t in proj.get("technologies") or []])
                if skill_lower in proj_desc.lower():
                    used = True
                    break
                    
        if used:
            validated_count += 1
        else:
            unsupported_skills.append(skill)
            
    validation_ratio = validated_count / len(skills)
    penalty = -8.0 if validation_ratio < 0.5 else 0.0
    return {
        "validation_ratio": round(validation_ratio, 2),
        "unsupported_skills": unsupported_skills,
        "penalty": penalty
    }


def _calculate_buzzword_penalty(resume_text: str) -> dict:
    buzzwords = [
        "strategic thinker", "results-driven", "results driven", "go-getter", "go getter", 
        "highly motivated", "team player", "detail-oriented", "detail oriented", "synergy", 
        "think outside the box", "thought leader", "paradigm shift", "seasoned professional", 
        "proven track record", "self-starter", "self starter", "hard worker", "dynamic"
    ]
    if not resume_text:
        return {"density": 0.0, "penalty": 0.0, "count": 0}
        
    text_lower = resume_text.lower()
    words = text_lower.split()
    total_words = len(words)
    if total_words == 0:
        return {"density": 0.0, "penalty": 0.0, "count": 0}
        
    count = 0
    found = []
    for b in buzzwords:
        matches = re.findall(r'\b' + re.escape(b) + r'\b', text_lower)
        if matches:
            count += len(matches)
            found.append(b)
            
    density = (count / total_words) * 100
    penalty = 0.0
    if count >= 10 or density > 2.0:
        penalty = -5.0
    return {
        "count": count,
        "density": round(density, 2),
        "found": found,
        "penalty": penalty
    }


def _calculate_timeline_gaps(resume_parsed: dict) -> dict:
    experience_entries = resume_parsed.get("experience") or []
    ranges = []
    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue
        start_str = entry.get("start_date") or ""
        end_str = entry.get("end_date") or ""
        start_m = _parse_date_to_months(start_str)
        end_m = _parse_date_to_months(end_str)
        if start_m and end_m:
            ranges.append((start_m, end_m))
            
    if len(ranges) < 2:
        return {"max_gap_months": 0, "penalty": 0.0}
        
    ranges.sort(key=lambda x: x[0])
    
    max_gap = 0
    current_end = ranges[0][1]
    for i in range(1, len(ranges)):
        start, end = ranges[i]
        if start > current_end:
            gap = start - current_end
            if gap > max_gap:
                max_gap = gap
        current_end = max(current_end, end)
        
    penalty = -15.0 if max_gap > 12 else 0.0
    return {
        "max_gap_months": max_gap,
        "penalty": penalty
    }


def _detect_upward_trajectory(resume_parsed: dict) -> dict:
    experience_entries = resume_parsed.get("experience") or []
    entries_sorted = []
    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue
        start_m = _parse_date_to_months(entry.get("start_date") or "")
        if start_m:
            entries_sorted.append((start_m, entry.get("role", "")))
    entries_sorted.sort(key=lambda x: x[0])
    
    levels = []
    for _, role in entries_sorted:
        r_lower = role.lower()
        if "lead" in r_lower or "principal" in r_lower or "manager" in r_lower or "director" in r_lower or "head" in r_lower:
            levels.append(3)
        elif "senior" in r_lower or "sr" in r_lower:
            levels.append(2)
        elif "junior" in r_lower or "jr" in r_lower or "intern" in r_lower:
            levels.append(0)
        else:
            levels.append(1)
            
    has_upward = False
    if len(levels) >= 2:
        for i in range(1, len(levels)):
            if levels[i] > levels[i-1]:
                has_upward = True
                break
    return {
        "has_upward": has_upward,
        "levels": levels,
        "bonus": 3.0 if has_upward else 0.0
    }


def _detect_rehired(resume_parsed: dict) -> dict:
    experience_entries = resume_parsed.get("experience") or []
    companies = []
    for entry in experience_entries:
        if isinstance(entry, dict) and entry.get("company"):
            companies.append(str(entry.get("company")).strip().lower())
            
    from collections import Counter
    counts = Counter(companies)
    rehired = any(count >= 2 for count in counts.values() if count)
    return {
        "rehired": rehired,
        "bonus": 2.0 if rehired else 0.0
    }

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


def _compute_experience_score(
    resume_parsed: dict,
    jd_extracted: dict,
) -> Dict[str, Any]:
    """Compare experience years and calculate relevance locally.

    This replaces the slow LLM experience scoring node, reducing pipeline latency
    by avoiding a roundtrip HTTP request and rate limit penalties.
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

    # Meets or exceeds: base 85 points + surplus years scaling up to 100
    if resume_years >= required_years:
        surplus = resume_years - required_years
        score = min(85.0 + surplus * 3.0, 100.0)
        verdict = f"Meets or exceeds minimum requirement ({resume_years:.1f} of {required_years:.1f} years)."
    else:
        # Below: scale proportionally up to 75
        ratio = resume_years / required_years
        score = round(ratio * 75.0, 1)
        verdict = f"Below minimum requirement: has {resume_years:.1f} of {required_years:.1f} required years."

    return {
        "score": min(max(round(score, 1), 0.0), 100.0),
        "detail": {
            "resume_years": resume_years,
            "required_years": required_years,
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
        
        if isinstance(exp_score_val, dict):
            score_val = exp_score_val.get("score", 0)
            score = float(score_val) if score_val is not None else 0.0
            verdict = exp_score_val.get("verdict", "")
        else:
            score = float(exp_score_val) if exp_score_val is not None else 0.0
            verdict = data.get("verdict", "") or ""

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
    return _compute_experience_score(resume_parsed, jd_extracted)


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
    scoring and industrial validation flags.
    """
    if state.get("error"):
        return {}

    resume_skills: List[str] = state.get("resume_skills_normalized", [])
    jd_skills: List[str] = state.get("jd_skills_normalized", [])
    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})
    resume_text: str = state.get("resume_text", "")
    jd_text: str = state.get("jd_text", "")

    # ── 1. Keyword overlap (Hard Skills) ──────────────────────────────────
    keyword_result = compute_keyword_overlap(resume_skills, jd_skills)
    keyword_score: float = keyword_result.get("score", 0.0)
    matched_skills: List[str] = keyword_result.get("matched", [])
    missing_skills: List[str] = keyword_result.get("missing", [])
    overlap_pct: float = keyword_result.get("overlap_pct", 0.0)

    # ── 2. Skill Recency ──────────────────────────────────────────────────
    recency_score = _calculate_skill_recency_score(resume_parsed, jd_skills)

    # ── 3. Experience Relevance ───────────────────────────────────────────
    exp_result = _compute_experience_score(resume_parsed, jd_extracted)
    experience_score: float = exp_result["score"]

    # ── 4. Education & Certs ──────────────────────────────────────────────
    edu_result = _compute_education_score(resume_parsed, jd_extracted)
    education_score: float = edu_result["score"]

    # ── 5. Semantic similarity ────────────────────────────────────────────
    semantic_score: float = compute_semantic_score(resume_text, jd_text)

    # ── 6. Achievement Quality (A-COE) ────────────────────────────────────
    achievement_score = _calculate_achievement_quality(resume_parsed)

    # ── 7. Buzzword Density & Quality ─────────────────────────────────────
    buzz_res = _calculate_buzzword_penalty(resume_text)

    # ── 8. Red Flags & Gaps Calculations ──────────────────────────────────
    gap_res = _calculate_timeline_gaps(resume_parsed)
    hopping_res = _detect_job_hopping(resume_parsed)
    validation_res = _validate_skills_against_experience(resume_parsed)

    # Compile Red Flags
    red_flags = []
    disqualified = False
    disqualification_reason = ""

    # AI Generated Check
    ai_prob = resume_parsed.get("ai_resume_probability", 0.0)
    if ai_prob >= 0.85:
        red_flags.append({
            "flag": "AI-Generated Resume Template",
            "penalty": "AUTO_REJECT",
            "evidence": f"Stylistic footprint strongly aligns with AI generation patterns ({ai_prob*100:.1f}% probability)."
        })
        disqualified = True
        disqualification_reason = f"AI-generated content matches/exceeds safety threshold (current: {ai_prob*100:.1f}% vs max: 85.0%)."
    
    # Gap check
    if gap_res["penalty"] < 0:
        red_flags.append({
            "flag": "Timeline Gaps > 12 Months",
            "penalty": gap_res["penalty"],
            "evidence": f"Detected unexplained career timeline gap of {gap_res['max_gap_months']} months."
        })
    
    # Job hopping check
    if hopping_res["penalty"] < 0:
        red_flags.append({
            "flag": "Job Hopping Behavior",
            "penalty": hopping_res["penalty"],
            "evidence": f"Candidate has {hopping_res['short_tenure_count']} consecutive tenures shorter than 12 months without valid contract/project annotations."
        })
        
    # Skills context check
    if validation_res["penalty"] < 0:
        red_flags.append({
            "flag": "Skills Without Context (Fabrication Risk)",
            "penalty": validation_res["penalty"],
            "evidence": f"Only {validation_res['validation_ratio']*100:.1f}% of listed skills are mentioned in work experience or projects."
        })

    # Vague achievements check
    if achievement_score < 40.0:
        red_flags.append({
            "flag": "Vague Career Achievement Bullets",
            "penalty": -5.0,
            "evidence": f"Low occurrence of metrics, context, or results in experience descriptions ({achievement_score:.1f}% quality)."
        })

    # Buzzword check
    if buzz_res["penalty"] < 0:
        red_flags.append({
            "flag": "Buzzword Overload",
            "penalty": buzz_res["penalty"],
            "evidence": f"Generic buzzword count exceeds acceptable density ({buzz_res['count']} buzzwords, {buzz_res['density']}% of text)."
        })

    # Compile Green Flags
    green_flags = []
    
    # COE bonus
    if achievement_score >= 70.0:
        green_flags.append({
            "flag": "COE Formatted Bullets",
            "bonus": 5.0,
            "evidence": f"Highly quantitative bullets demonstrating Action + Context + Outcome + Evidence ({achievement_score:.1f}% quality)."
        })
        
    # Summary alignment check
    summary_text = str(resume_parsed.get("summary") or "").lower()
    target_title = str(jd_extracted.get("job_title") or "").lower()
    if target_title and any(w in summary_text for w in target_title.split() if len(w) > 3):
        green_flags.append({
            "flag": "Alignment Hero Section",
            "bonus": 3.0,
            "evidence": "Professional summary demonstrates immediate target role alignment."
        })

    # Skills mirroring bonus
    if validation_res["validation_ratio"] >= 0.80:
        green_flags.append({
            "flag": "Skill-JD Mirroring",
            "bonus": 4.0,
            "evidence": f"Excellent integration of skills within project descriptions ({validation_res['validation_ratio']*100:.1f}% validation rate)."
        })

    # Portfolio bonus
    portfolio_links = resume_parsed.get("portfolio_links") or []
    if portfolio_links:
        green_flags.append({
            "flag": "Portfolio Accessible",
            "bonus": 2.0,
            "evidence": f"Found accessible links: {', '.join(portfolio_links)}."
        })

    # Trajectory bonus
    upward_res = _detect_upward_trajectory(resume_parsed)
    if upward_res["bonus"] > 0:
        green_flags.append({
            "flag": "Upward Trajectory",
            "bonus": upward_res["bonus"],
            "evidence": "Timeline displays chronological progression of seniority and job level."
        })

    # Rehire bonus
    rehired_res = _detect_rehired(resume_parsed)
    if rehired_res["bonus"] > 0:
        green_flags.append({
            "flag": "Rehired by Same Employer",
            "bonus": rehired_res["bonus"],
            "evidence": "Repeated tenures at the same employer indicate performance re-engagement."
        })

    # ── 9. Weighted overall and match score calculations ──────────────────
    # Weights: Hard Skills (35%), Recency (15%), Experience (20%), Education (10%), Semantic (10%), Achievements (5%), Buzzwords (5%)
    w_skills = 0.35
    w_recency = 0.15
    w_exp = 0.20
    w_edu = 0.10
    w_sem = 0.10
    w_ach = 0.05
    w_buzz = 0.05
    
    overall_score = round(
        w_skills * keyword_score
        + w_recency * recency_score
        + w_exp * experience_score
        + w_edu * education_score
        + w_sem * semantic_score
        + w_ach * achievement_score
        + w_buzz * (100.0 + buzz_res["penalty"]),
        1,
    )

    penalty_total = sum(f["penalty"] for f in red_flags if isinstance(f["penalty"], (int, float)))
    bonus_total = sum(f["bonus"] for f in green_flags)
    match_score = overall_score + penalty_total + bonus_total
    match_score = min(max(round(match_score, 1), 0.0), 100.0)

    # ── Strengths & gaps ─────────────────────────────────────────────────
    strengths, gaps = _identify_strengths_and_gaps(
        matched_skills,
        missing_skills,
        exp_result["detail"],
        edu_result["detail"],
    )

    # Add red flags as gaps and green flags as strengths for unified visibility
    for rf in red_flags:
        gaps.append(f"Red Flag: {rf['flag']} ({rf['evidence']})")
    for gf in green_flags:
        strengths.append(f"Green Flag: {gf['flag']} ({gf['evidence']})")

    logger.info(
        "Industrial scores — base overall: %.1f, final match: %.1f, disqualified: %s",
        overall_score,
        match_score,
        disqualified,
    )

    component_scores = {
        "hard_skills": keyword_score,
        "recency": recency_score,
        "experience": experience_score,
        "education": education_score,
        "semantic": semantic_score,
        "achievements": achievement_score
    }

    return {
        "keyword_score": keyword_score,
        "semantic_score": semantic_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "overall_score": overall_score,
        "recency_score": recency_score,
        "achievement_score": achievement_score,
        "match_score": match_score,
        "disqualified": disqualified,
        "disqualification_reason": disqualification_reason,
        "job_hopping_info": hopping_res,
        "skills_validation": validation_res,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "component_scores": component_scores,
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
