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
    if state.get("error"):
        return {}

    gaps: List[str] = state.get("gaps", [])
    skill_match: dict = state.get("skill_match", {})
    resume_parsed: dict = state.get("resume_parsed", {})
    jd_extracted: dict = state.get("jd_extracted", {})
    overall_score: float = state.get("overall_score", 0.0)
    strengths: List[str] = state.get("strengths", [])

    missing_skills: List[str] = skill_match.get("missing", [])

    # Collect existing resume bullets for rewriting
    experience_entries = resume_parsed.get("experience") or []
    existing_bullets: List[str] = []
    for entry in experience_entries:
        if entry and isinstance(entry, dict):
            bullets = entry.get("bullets") or []
            existing_bullets.extend(b for b in bullets if b)

    try:
        import time
        from core.telemetry import TelemetryLogger
        from config.prompt_registry import PromptRegistry

        start_time = time.time()
        llm, provider = resume_parser.get_llm()

        system_prompt = PromptRegistry.get_prompt("improver", version="v1.0.0")
        prompt = (
            f"{system_prompt}\n\n"
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
        
        latency = time.time() - start_time
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(raw_content) // 4
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

        TelemetryLogger.record_event(
            node_name="improve_resume",
            provider=provider,
            latency_sec=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success"
        )

        # ── Extract improvement suggestions ───────────────────────────────
        # The LLM prompt uses multiple output keys; we normalize them all
        # into two unified lists for the UI.

        suggestions: List[Any] = []

        # 1. Section-level suggestions (from prompt schema: "section_suggestions")
        section_suggestions = data.get("section_suggestions", [])
        for item in section_suggestions:
            if isinstance(item, dict):
                section = item.get("section", "General")
                suggestion = item.get("suggestion", "")
                impact = item.get("impact", "Medium")
                if suggestion:
                    suggestions.append({
                        "suggestion": f"[{section}] {suggestion}",
                        "impact": impact,
                    })
            elif isinstance(item, str) and item:
                suggestions.append({"suggestion": item, "impact": "Medium"})

        # 2. Skills to add (from prompt schema: "skills_to_add")
        skills_to_add = data.get("skills_to_add", [])
        for item in skills_to_add:
            if isinstance(item, dict):
                skill = item.get("skill", "")
                rationale = item.get("rationale", "")
                evidence = item.get("evidence", "")
                if skill:
                    text = f"Add '{skill}' to your skills section"
                    if evidence:
                        text += f" — your experience ({evidence}) supports this"
                    if rationale:
                        text += f". {rationale}"
                    suggestions.append({"suggestion": text, "impact": "High"})
            elif isinstance(item, str) and item:
                suggestions.append({"suggestion": f"Add skill: {item}", "impact": "High"})

        # 3. Skills reorder (from prompt schema: "skills_to_reorder")
        skills_reorder = data.get("skills_to_reorder", {})
        if isinstance(skills_reorder, dict) and skills_reorder.get("suggested_order"):
            suggested = ", ".join(skills_reorder["suggested_order"][:8])
            rationale = skills_reorder.get("rationale", "")
            suggestions.append({
                "suggestion": f"Reorder your skills to lead with JD-priority items: {suggested}. {rationale}",
                "impact": "Medium",
            })

        # 4. Missing keywords (from prompt schema: "missing_keywords")
        missing_kw = data.get("missing_keywords", [])
        if missing_kw:
            kw_list = ", ".join(str(k) for k in missing_kw[:10])
            suggestions.append({
                "suggestion": f"Incorporate these missing JD keywords naturally into your resume: {kw_list}",
                "impact": "High",
            })

        # 5. Overall summary (from prompt schema: "summary")
        summary = data.get("summary", "")
        if summary:
            suggestions.append({
                "suggestion": summary,
                "impact": "General",
            })

        # 6. Score improvement estimate
        est_improvement = data.get("estimated_score_improvement")
        if est_improvement is not None:
            try:
                est_val = float(est_improvement)
                suggestions.append({
                    "suggestion": f"Estimated ATS score after implementing these changes: {est_val:.1f}/100 (current: {overall_score:.1f})",
                    "impact": "Projection",
                })
            except (ValueError, TypeError):
                pass

        # 7. Fallback: if LLM returned flat "improvement_suggestions"
        fallback_suggestions = data.get("improvement_suggestions", [])
        if fallback_suggestions and not suggestions:
            for item in fallback_suggestions:
                if isinstance(item, dict):
                    suggestions.append(item)
                elif isinstance(item, str) and item:
                    suggestions.append({"suggestion": item, "impact": "Medium"})

        # ── Extract ATS-optimized bullets ─────────────────────────────────
        optimized_bullets: List[Any] = []

        # From prompt schema: "improved_bullets"
        improved_bullets = data.get("improved_bullets", [])
        for item in improved_bullets:
            if isinstance(item, dict):
                optimized_bullets.append({
                    "original": item.get("original", ""),
                    "improved": item.get("improved", ""),
                    "keywords_added": item.get("keywords_added", []),
                    "rationale": item.get("rationale", ""),
                })
            elif isinstance(item, str) and item:
                optimized_bullets.append({"original": "", "improved": item, "keywords_added": []})

        # Fallback: if LLM returned flat "ats_optimized_bullets"
        fallback_bullets = data.get("ats_optimized_bullets", [])
        if fallback_bullets and not optimized_bullets:
            for item in fallback_bullets:
                if isinstance(item, dict):
                    optimized_bullets.append(item)
                elif isinstance(item, str) and item:
                    optimized_bullets.append({"original": "", "improved": item, "keywords_added": []})

        # Ensure we always have lists
        if not isinstance(suggestions, list):
            suggestions = [{"suggestion": str(suggestions), "impact": "Medium"}]
        if not isinstance(optimized_bullets, list):
            optimized_bullets = [{"original": "", "improved": str(optimized_bullets), "keywords_added": []}]

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
        latency = time.time() - start_time if 'start_time' in locals() else 0.0
        logger.exception("Improvement generation failed.")
        
        from core.telemetry import TelemetryLogger
        TelemetryLogger.record_event(
            node_name="improve_resume",
            provider="failed",
            latency_sec=latency,
            prompt_tokens=0,
            completion_tokens=0,
            status="failed",
            error_msg=str(exc)
        )

        err_msg = str(exc).lower()
        if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
            return {
                "improvement_suggestions": [],
                "ats_optimized_bullets": [],
                "error": "API Quota Exhausted: Groq/Gemini rate limit exceeded. Please wait 1-2 minutes and try again.",
            }
        return {
            "improvement_suggestions": [
                {
                    "suggestion": "Unable to generate suggestions automatically. "
                    "Review the gaps list and incorporate missing skills.",
                    "impact": "General",
                }
            ],
            "ats_optimized_bullets": [],
            "error": f"Improvement generation failed: {exc}",
        }
