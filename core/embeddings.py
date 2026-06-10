"""
Sentence-transformer embeddings module.

Provides a cached (singleton) ``SentenceTransformer`` model and convenience
helpers to embed one or many texts into dense vectors.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model cache (singleton, thread-safe)
# ---------------------------------------------------------------------------

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()


def get_embedding_model() -> SentenceTransformer:
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
                _model = SentenceTransformer(_MODEL_NAME)
                logger.info("Model loaded successfully.")
    return _model


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
