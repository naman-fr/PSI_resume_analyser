"""
Sentence-transformer embeddings module.

Provides a cached (singleton) ``SentenceTransformer`` model and convenience
helpers to embed one or many texts into dense vectors.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model cache (singleton, thread-safe)
# ---------------------------------------------------------------------------

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[Any] = None
_model_lock = threading.Lock()


def get_embedding_model() -> Any:
    """
    Return the cached ``SentenceTransformer`` model instance.

    The model is loaded lazily on the first call and reused for all
    subsequent calls.  Access is protected by a lock so concurrent
    threads never trigger a double-load.
    """
    global _model
    if _model is None:
        with _model_lock:
            # Double-checked locking
            if _model is None:
                logger.info("Loading sentence-transformer model '%s' …", _MODEL_NAME)
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(_MODEL_NAME)
                logger.info("Model loaded successfully.")
    return _model


# ---------------------------------------------------------------------------
# API Fallbacks (Low Memory / Render Free Tier)
# ---------------------------------------------------------------------------

def _get_hf_embeddings(texts: list[str]) -> Optional[np.ndarray]:
    """Query Hugging Face Inference API for embeddings (zero local RAM)."""
    import urllib.request
    import json
    import os

    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PSI-Resume-Analyser/1.0"
    }
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    payload = {"inputs": texts, "options": {"wait_for_model": True}}

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if isinstance(res_data, list) and len(res_data) > 0:
                logger.info("Successfully fetched embeddings from Hugging Face Inference API.")
                return np.array(res_data)
    except Exception as e:
        logger.warning(f"Hugging Face Inference API failed: {e}. Falling back.")
    return None


def _get_gemini_embeddings(texts: list[str]) -> Optional[np.ndarray]:
    """Query Google Gemini API for embeddings (zero local RAM)."""
    import urllib.request
    import json
    import os

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PSI-Resume-Analyser/1.0"
    }

    requests_list = [
        {"model": "models/text-embedding-004", "content": {"parts": [{"text": t}]}} for t in texts
    ]
    payload = {"requests": requests_list}

    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            embeddings = []
            if "embeddings" in res_data:
                for emb in res_data["embeddings"]:
                    if "values" in emb:
                        embeddings.append(emb["values"])
                if len(embeddings) == len(texts):
                    logger.info("Successfully fetched embeddings from Google Gemini API.")
                    return np.array(embeddings)
    except Exception as e:
        logger.warning(f"Gemini Embeddings API failed: {e}. Falling back.")
    return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Compute dense embeddings for a list of texts.

    Parameters
    ----------
    texts:
        A list of strings to embed.

    Returns
    -------
    numpy.ndarray
        A 2-D array of shape ``(len(texts), embedding_dim)``.
        Returns an empty array with shape ``(0,)`` when *texts* is empty.
    """
    if not texts:
        logger.warning("get_embeddings called with empty list; returning empty array.")
        return np.array([])

    # 1. Try Hugging Face Inference API
    hf_emb = _get_hf_embeddings(texts)
    if hf_emb is not None:
        return hf_emb

    # 2. Try Gemini Embeddings API
    gemini_emb = _get_gemini_embeddings(texts)
    if gemini_emb is not None:
        return gemini_emb

    # 3. Fallback to Local SentenceTransformer (heavy PyTorch setup)
    logger.info("Falling back to local SentenceTransformer model.")
    model = get_embedding_model()
    embeddings: np.ndarray = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    logger.debug("Encoded %d texts → shape %s", len(texts), embeddings.shape)
    return embeddings


def get_single_embedding(text: str) -> np.ndarray:
    """
    Compute the dense embedding for a single text string.

    Parameters
    ----------
    text:
        The input text to embed.

    Returns
    -------
    numpy.ndarray
        A 1-D array of shape ``(embedding_dim,)``.
        Returns an empty array when *text* is empty or whitespace-only.
    """
    if not text or not text.strip():
        logger.warning("get_single_embedding called with blank text; returning empty array.")
        return np.array([])

    embeddings = get_embeddings([text])
    return embeddings[0]


# perf: optimize embeddings helper using cached models singleton
