"""
Resume-parser agent node.

Parses raw resume text into a structured JSON dictionary using an LLM.
Gemini is the primary provider; Groq is the automatic fallback.
"""

import json
import logging
import re
from typing import Any, Dict, Tuple

from langchain_core.language_models.chat_models import BaseChatModel

from agents.state import ResumeJDState
from config.prompts import RESUME_PARSER_PROMPT

logger = logging.getLogger(__name__)


# ── LLM factory (reused by other agent modules) ────────────────────────────

def get_llm() -> Tuple[BaseChatModel, str]:
    """Return an LLM instance and the provider name.

    Tries **Google Gemini** first (via ``langchain-google-genai``).  If that
    import or instantiation fails for any reason, falls back to **Groq**.

    Returns
    -------
    (llm, provider_name)
        A ready-to-invoke ``BaseChatModel`` and a human-readable provider tag.
    """
    # --- Attempt 1: Gemini ------------------------------------------------
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config.settings import settings

        llm = ChatGoogleGenerativeAI(
            model=settings.models.gemini_model,
            google_api_key=settings.models.gemini_api_key,
            temperature=0.0,
            convert_system_message_to_human=True,
        )
        logger.info("LLM provider: Gemini (%s)", settings.models.gemini_model)
        return llm, "gemini"
    except Exception as exc:
        logger.warning("Gemini unavailable (%s), falling back to Groq.", exc)

    # --- Attempt 2: Groq --------------------------------------------------
    try:
        from langchain_groq import ChatGroq
        from config.settings import settings

        llm = ChatGroq(
            model=settings.models.groq_model,
            groq_api_key=settings.models.groq_api_key,
            temperature=0.0,
        )
        logger.info("LLM provider: Groq (%s)", settings.models.groq_model)
        return llm, "groq"
    except Exception as exc:
        raise RuntimeError(
            "No LLM provider available. Set GOOGLE_API_KEY or GROQ_API_KEY."
        ) from exc


# ── Helpers ─────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output.

    1. Try ``json.loads`` on the raw string directly.
    2. If that fails, look for a fenced code block (```json … ```) and parse
       the content inside it.
    3. If all else fails, raise ``ValueError``.
    """
    # Fast path
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Regex fallback: extract first JSON block from markdown fences
    pattern = r"```(?:json)?\s*\n?(.*?)```"
    match = re.search(pattern, raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Last resort: find the first { … } pair
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from LLM response.")


# ── Agent node ──────────────────────────────────────────────────────────────

def parse_resume(state: ResumeJDState) -> Dict[str, Any]:
    """LangGraph node: parse ``resume_text`` into ``resume_parsed``.

    Expected output schema (set in ``resume_parsed``)::

        {
            "name": str,
            "email": str,
            "phone": str,
            "summary": str,
            "skills": [str, ...],
            "experience": [
                {"title": str, "company": str, "duration": str, "bullets": [str]},
                ...
            ],
            "education": [
                {"degree": str, "institution": str, "year": str},
                ...
            ],
            "certifications": [str, ...],
            "total_experience_years": float
        }
    """
    resume_text: str = state.get("resume_text", "")
    if not resume_text.strip():
        return {"error": "resume_text is empty — nothing to parse."}

    try:
        llm, provider = get_llm()

        prompt = f"{RESUME_PARSER_PROMPT}\n\n## Input Resume Text\n{resume_text}"
        response = llm.invoke(prompt)
        raw_content: str = response.content  # type: ignore[union-attr]

        parsed: dict = _extract_json(raw_content)

        logger.info("Resume parsed successfully via %s.", provider)
        return {
            "resume_parsed": parsed,
            "provider_used": provider,
        }

    except Exception as exc:
        logger.exception("Resume parsing failed.")
        return {"error": f"Resume parsing failed: {exc}"}

# fix: replace .format() with f-string to prevent KeyError on literal braces
