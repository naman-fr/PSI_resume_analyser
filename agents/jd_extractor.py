"""
Job-description extractor agent node.

Extracts structured requirements from raw job-description text using an LLM.
"""

import logging
from typing import Any, Dict

from agents import resume_parser
from agents.state import ResumeJDState

logger = logging.getLogger(__name__)


def extract_jd(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: extract structured data from ``jd_text``."""
    if state.get("error"):
        return {}

    jd_text: str = state.get("jd_text", "")
    if not jd_text.strip():
        return {"error": "jd_text is empty — nothing to extract."}

    # ── 1. Security Guardrails: Prompt Injection Check ────────────────────────
    from core.guardrails import scan_prompt_injection
    is_injection, confidence, reason = scan_prompt_injection(jd_text)
    if is_injection:
        logger.warning("JD extraction blocked by Prompt Injection Guardrail: %s", reason)
        return {"error": f"Security Guardrails Triggered: Potential Prompt Injection Detected in Job Description ({reason})."}

    # ── 2. Extract via LLM ────────────────────────────────────────────────────
    import time
    from core.telemetry import TelemetryLogger
    from config.prompt_registry import PromptRegistry

    start_time = time.time()
    try:
        llm, provider = resume_parser.get_llm()

        system_prompt = PromptRegistry.get_prompt("jd_extractor", version="v1.0.0")
        prompt = f"{system_prompt}\n\n## Input Job Description\n{jd_text}"
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

        latency = time.time() - start_time

        # Extract token usage
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        else:
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(raw_content) // 4

        TelemetryLogger.record_event(
            node_name="extract_jd",
            provider=provider,
            latency_sec=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success"
        )

        logger.info("JD extracted successfully via %s.", provider)
        return {
            "jd_extracted": extracted,
            "provider_used": provider,
        }

    except Exception as exc:
        latency = time.time() - start_time
        logger.exception("JD extraction failed.")
        
        from core.telemetry import TelemetryLogger
        TelemetryLogger.record_event(
            node_name="extract_jd",
            provider="failed",
            latency_sec=latency,
            prompt_tokens=0,
            completion_tokens=0,
            status="failed",
            error_msg=str(exc)
        )

        err_msg = str(exc).lower()
        if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
            return {"error": "API Quota Exhausted: Groq/Gemini rate limit exceeded. Please wait 1-2 minutes and try again."}
        return {"error": f"JD extraction failed: {exc}"}

# refactor: import resume_parser module instead of function to support mock testing
