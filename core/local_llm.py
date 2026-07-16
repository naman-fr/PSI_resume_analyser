"""
Local LLM Provider — Ollama-backed Tier 0 inference.
Mirrors the interface contract of get_llm() in agents/resume_parser.py
so it's a drop-in provider, not a fork of the pipeline.
"""
import logging
import os
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_MODEL = "qwen2.5:7b-instruct-q4_K_M"

def get_local_llm(model: str = DEFAULT_LOCAL_MODEL, temperature: float = 0.0, format_json: bool = True):
    """
    Returns a LangChain-compatible ChatOllama instance.
    format_json=True enables Ollama's grammar-constrained JSON mode,
    which compensates for weaker structured-output adherence vs Gemini/Groq.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    
    kwargs = {
        "model": model,
        "temperature": temperature,
        "base_url": base_url,
    }
    if format_json:
        kwargs["format"] = "json"   # constrained decoding, not just a prompt hint
        
    return ChatOllama(**kwargs)

def is_ollama_available() -> bool:
    """Health check so the router can fail over silently if Ollama isn't running."""
    import requests
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False
