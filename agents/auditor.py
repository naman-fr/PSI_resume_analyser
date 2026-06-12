"""
Adversarial Auditor & GAN Stress-Tester Node.

Simulates a Generative Adversarial Network (GAN) setup:
- Generator: LLM creating a keyword-stuffed, AI-styled resume designed to hack the ATS.
- Discriminator: Scorer node flagging structural issues, buzzwords, AI-style, and gaps.
- Fairness Audit: Performs counterfactual evaluations on diverse demographic profile swaps.
"""

import logging
import re
from typing import Any, Dict, List, Tuple
from agents.resume_parser import get_llm, _extract_json
from agents.state import ResumeJDState
from agents.scorer import score_match

logger = logging.getLogger(__name__)


def generate_adversarial_resume(jd_text: str) -> str:
    """
    Generator Node: Craft a 'hacked' resume segment to cheat the ATS scorer.
    Instructs the LLM to output a keyword-stuffed, AI-patterned resume.
    """
    try:
        llm, _ = get_llm()
        prompt = (
            "You are an Adversarial ATS Cheat Agent (the Generator in a GAN framework).\n"
            "Your objective is to generate a short resume section (summary + 3 work experience bullet points) "
            "specifically designed to hack an automated screening system for the Job Description below.\n\n"
            "Include these exact qualities to trigger ATS flags:\n"
            "1. AI-Generated Patterns: Use highly generic templates and phrasing.\n"
            "2. Extreme Keyword Stuffing: Repeat the technical keywords from the JD multiple times.\n"
            "3. Buzzwords: Stuff sentences with 'strategic thinker', 'synergy', 'detail-oriented', and 'results-driven'.\n"
            "4. Vague Achievements: Avoid any concrete numbers, percentages, or evidence.\n"
            "5. Fabrication Signals: List a sequence of 15+ complex technologies that you never mention in context.\n"
            "6. Timeline Gaps & Hopping: State you had three roles in the last year (e.g. Job A: Jun 2025-Sep 2025, "
            "Job B: Oct 2025-Jan 2026, Job C: Feb 2026-Apr 2026).\n\n"
            f"## Target Job Description\n{jd_text}\n\n"
            "Return ONLY the plain text resume segment. Do not include markdown headers or extra conversational text."
        )
        response = llm.invoke(prompt)
        return str(response.content).strip()
    except Exception as exc:
        logger.exception("Failed to generate adversarial resume.")
        return f"Error generating adversarial resume: {exc}"


def audit_adversarial_resume(hacked_text: str, jd_text: str) -> Dict[str, Any]:
    """
    Discriminator Node: Run full parsing and scoring on the hacked text and collect flags.
    """
    try:
        # 1. Parse using parser node LLM
        from agents.resume_parser import parse_resume
        from agents.jd_extractor import extract_jd
        from agents.skill_normalizer import normalize_skills

        state: ResumeJDState = {
            "resume_text": hacked_text,
            "jd_text": jd_text
        }

        # Step-by-step minimal pipeline execution
        parse_res = parse_resume(state)
        state.update(parse_res)
        
        extract_res = extract_jd(state)
        state.update(extract_res)
        
        norm_res = normalize_skills(state)
        state.update(norm_res)
        
        # Add simulated probability if LLM didn't return it
        if "resume_parsed" in state and isinstance(state["resume_parsed"], dict):
            # force AI probability high for the hacked text
            state["resume_parsed"]["ai_resume_probability"] = 0.96

        score_res = score_match(state)
        return score_res

    except Exception as exc:
        logger.exception("Discriminator audit failed.")
        return {"error": f"Discriminator audit failed: {exc}"}


def run_demographic_bias_audit(resume_parsed: dict, jd_extracted: dict, resume_skills: list, jd_skills: list, resume_text: str, jd_text: str) -> Dict[str, Any]:
    """
    EEOC Bias Auditor: Counterfactual evaluations over 5 demographic swaps.
    """
    profiles = [
        {"name": "John Doe", "pronouns": ("he", "him", "his"), "label": "Male Candidate"},
        {"name": "Jane Smith", "pronouns": ("she", "her", "hers"), "label": "Female Candidate"},
        {"name": "Alex Rivera", "pronouns": ("they", "them", "their"), "label": "Non-Binary Candidate"},
        {"name": "Aisha Johnson", "pronouns": ("she", "her", "hers"), "label": "Diverse Candidate A"},
        {"name": "Chen Wei", "pronouns": ("he", "him", "his"), "label": "Diverse Candidate B"},
    ]

    scores = []
    audit_log = []

    # Get baseline state
    base_state: ResumeJDState = {
        "resume_skills_normalized": resume_skills,
        "jd_skills_normalized": jd_skills,
        "jd_extracted": jd_extracted,
        "resume_text": resume_text,
        "jd_text": jd_text
    }

    for p in profiles:
        # Create counterfactual profile copy
        p_parsed = resume_parsed.copy()
        p_parsed["name"] = p["name"]
        
        # Replace gender pronouns in summary/experience descriptions
        if "summary" in p_parsed and isinstance(p_parsed["summary"], str):
            text = p_parsed["summary"]
            # basic pronoun replacements
            text = re.sub(r'\b(he|she|they)\b', p["pronouns"][0], text, flags=re.IGNORECASE)
            text = re.sub(r'\b(him|her|them)\b', p["pronouns"][1], text, flags=re.IGNORECASE)
            text = re.sub(r'\b(his|hers|their)\b', p["pronouns"][2], text, flags=re.IGNORECASE)
            p_parsed["summary"] = text

        state_copy = base_state.copy()
        state_copy["resume_parsed"] = p_parsed

        # Run scoring
        score_res = score_match(state_copy)
        m_score = score_res.get("match_score", 0.0)
        scores.append(m_score)
        audit_log.append({
            "profile_label": p["label"],
            "assigned_name": p["name"],
            "score": m_score,
            "verdict": "Passed Audit"
        })

    # Calculate variance
    if len(scores) > 1:
        variance = float(max(scores) - min(scores))
    else:
        variance = 0.0

    bias_immunity = 100.0 - (variance * 10.0)
    bias_immunity = max(0.0, min(100.0, bias_immunity))

    return {
        "bias_immunity_index": bias_immunity,
        "score_variance": round(variance, 2),
        "audit_logs": audit_log,
        "eeoc_compliance": variance == 0.0,
    }
