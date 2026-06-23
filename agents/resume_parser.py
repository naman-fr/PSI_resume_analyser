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

logger = logging.getLogger(__name__)


# ── LLM factory (reused by other agent modules) ────────────────────────────

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class MockChatModel(BaseChatModel):
    """Local simulation mock model when no live API keys are provided."""
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        prompt_text = "".join(str(m.content) for m in messages)
        response_text = "{}"
        
        # Analyze prompt and simulate structured output
        if "improver" in prompt_text.lower() or "optimize" in prompt_text.lower() or "star" in prompt_text.lower():
            response_text = json.dumps({
                "ats_optimized_bullets": [
                    "Spearheaded Python FastAPI backend API development, scaling throughput by 40% and reducing server response latency by 200ms.",
                    "Architected high-performance PostgreSQL database schemas, optimizing complex queries to improve search speeds by 35%.",
                    "Orchestrated Docker containerization for 12+ microservices, unifying development environments and cutting deployment times by 50%."
                ]
            })
        elif "parser" in prompt_text.lower() or "resume" in prompt_text.lower():
            response_text = json.dumps({
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+1-123-456-7890",
                "skills": ["Python", "Docker", "SQL", "FastAPI"],
                "experience": [
                    {
                        "company": "Tech Corp",
                        "title": "Software Engineer",
                        "bullets": ["Developed APIs", "Optimized DB"]
                    }
                ]
            })
        elif "scorer" in prompt_text.lower() or "alignment" in prompt_text.lower():
            response_text = json.dumps({
                "match_score": 85.0,
                "keyword_score": 80.0,
                "semantic_score": 90.0,
                "strengths": ["Strong Python experience", "Containerization skills"],
                "gaps": ["Lacks cloud architecture experience"]
            })
        elif "critic" in prompt_text.lower():
            response_text = json.dumps({
                "is_valid": True,
                "confidence_score": 0.95,
                "feedback_details": ""
            })
        elif "planner" in prompt_text.lower():
            response_text = json.dumps({
                "plan_steps": ["Parse resume", "Scan JDs", "Score alignment"],
                "focus_areas": ["Python backend", "Database optimization"],
                "targeted_version": "v1.0.0"
            })
        else:
            response_text = json.dumps({
                "match_score": 75.0,
                "keyword_score": 70.0,
                "semantic_score": 80.0,
                "strengths": ["Strong engineering background"],
                "gaps": ["Lacks specialized certifications"]
            })
            
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
        
    def _llm_type(self) -> str:
        return "mock-chat-model"

def get_llm() -> Tuple[BaseChatModel, str]:
    """Return the Groq LLM instance or a MockChatModel fallback."""
    import os
    from config.settings import settings
    
    api_key = settings.models.groq_api_key or os.environ.get("GROQ_API_KEY")
    if not api_key or "placeholder" in api_key.lower():
        logger.info("GROQ_API_KEY is missing or contains placeholder. Initializing local Mock Simulation LLM.")
        return MockChatModel(), "mock"

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=settings.models.groq_model,
            groq_api_key=api_key,
            temperature=0.0,
        )
        logger.info("LLM provider: Groq (%s)", settings.models.groq_model)
        return llm, "groq"
    except Exception as exc:
        logger.warning("Failed to initialize Groq client: %s. Falling back to Mock Simulation LLM.", exc)
        return MockChatModel(), "mock"


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
    """LangGraph node: parse ``resume_text`` into ``resume_parsed``."""
    resume_text: str = state.get("resume_text", "")
    if not resume_text.strip():
        return {"error": "resume_text is empty — nothing to parse."}

    # ── 1. Security Guardrails: Prompt Injection Check ────────────────────────
    from core.guardrails import scan_prompt_injection, mask_pii
    is_injection, confidence, reason = scan_prompt_injection(resume_text)
    if is_injection:
        logger.warning("Resume parsing blocked by Prompt Injection Guardrail: %s", reason)
        return {"error": f"Security Guardrails Triggered: Potential Prompt Injection Detected ({reason})."}

    # ── 2. Security Guardrails: PII Anonymization ──────────────────────────────
    masked_text, redacting_map = mask_pii(resume_text)

    # Check Episodic Memory Cache (Cost & Latency Optimization) ────────────────
    from core.memory import MemoryManager
    cached_parsed = MemoryManager.lookup_parse_memory(resume_text)
    if cached_parsed:
        return {
            "resume_parsed": cached_parsed,
            "provider_used": "episodic_memory_cache",
            "redacting_map": redacting_map
        }

    # ── 3. Parse via LLM ──────────────────────────────────────────────────────
    import time
    from core.telemetry import TelemetryLogger
    from config.prompt_registry import PromptRegistry

    start_time = time.time()
    try:
        llm, provider = get_llm()

        system_prompt = PromptRegistry.get_prompt("resume_parser", version="v1.0.0")
        
        # Read self-reflection feedback if looping back
        feedback = state.get("critic_report", {}).get("feedback_details", "")
        if feedback:
            system_prompt += f"\n\n## Self-Correction Feedback (Resolve these issues!):\n{feedback}"
            logger.info("Injecting Critic feedback into Resume Parser: %s", feedback)

        prompt = f"{system_prompt}\n\n## Input Resume Text\n{masked_text}"
        response = llm.invoke(prompt)
        raw_content: str = response.content  # type: ignore[union-attr]

        parsed: dict = _extract_json(raw_content)
        latency = time.time() - start_time

        # Extract token counts for telemetry
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        else:
            # Token estimation fallback
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(raw_content) // 4

        # Record event in Telemetry log
        TelemetryLogger.record_event(
            node_name="parse_resume",
            provider=provider,
            latency_sec=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success"
        )

        # Cache in Episodic Memory
        MemoryManager.save_parse_to_memory(resume_text, parsed)

        logger.info("Resume parsed successfully via %s.", provider)
        return {
            "resume_parsed": parsed,
            "provider_used": provider,
            "redacting_map": redacting_map
        }

    except Exception as exc:
        latency = time.time() - start_time
        logger.exception("Resume parsing failed.")
        
        from core.telemetry import TelemetryLogger
        TelemetryLogger.record_event(
            node_name="parse_resume",
            provider="failed",
            latency_sec=latency,
            prompt_tokens=0,
            completion_tokens=0,
            status="failed",
            error_msg=str(exc)
        )

        err_msg = str(exc).lower()
        if any(term in err_msg for term in ["quota", "rate limit", "429", "rate_limit"]):
            return {"error": "API Quota Exhausted: Groq/Gemini rate limit exceeded. Resume parsing failed. Please wait 1-2 minutes and try again."}
        return {"error": f"Resume parsing failed: {exc}"}

# fix: replace .format() with f-string to prevent KeyError on literal braces
