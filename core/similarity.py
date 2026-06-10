"""
Similarity computation module.

Combines dense-vector cosine similarity (semantic) with exact keyword
overlap (lexical) to produce a composite match score between a resume
and a job description.
"""

from __future__ import annotations

import logging
from typing import Union

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

from core.embeddings import get_embeddings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level vector similarity
# ---------------------------------------------------------------------------


def compute_cosine_similarity(
    vec1: Union[np.ndarray, list[float]],
    vec2: Union[np.ndarray, list[float]],
) -> float:
    """
    Compute cosine similarity between two vectors.

    Parameters
    ----------
    vec1, vec2:
        1-D vectors of the same dimensionality.

    Returns
    -------
    float
        Cosine similarity in the range [-1, 1].
    """
    v1 = np.asarray(vec1).reshape(1, -1)
    v2 = np.asarray(vec2).reshape(1, -1)
    sim: float = float(sk_cosine(v1, v2)[0][0])
    return sim


# ---------------------------------------------------------------------------
# Keyword / skill overlap
# ---------------------------------------------------------------------------


def compute_keyword_overlap(
    resume_skills: list[str],
    jd_skills: list[str],
) -> dict:
    """
    Compute exact keyword overlap between resume skills and JD skills.

    Matching is case-insensitive.

    Parameters
    ----------
    resume_skills:
        Skills extracted from the resume.
    jd_skills:
        Skills required by the job description.

    Returns
    -------
    dict
        ``matched_skills``  – list of skills present in both sets.
        ``missing_skills``  – list of JD skills absent from the resume.
        ``overlap_percentage`` – 0-100 float indicating match rate.
    """
    resume_lower = {s.strip().lower() for s in resume_skills if s.strip()}
    jd_lower_to_original = {
        s.strip().lower(): s.strip() for s in jd_skills if s.strip()
    }

    matched: list[str] = []
    missing: list[str] = []

    for jd_lower, jd_original in jd_lower_to_original.items():
        if jd_lower in resume_lower:
            matched.append(jd_original)
        else:
            missing.append(jd_original)

    total = len(jd_lower_to_original)
    overlap_pct = (len(matched) / total * 100.0) if total > 0 else 0.0

    return {
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "overlap_percentage": round(overlap_pct, 2),
    }


# ---------------------------------------------------------------------------
# Composite semantic score
# ---------------------------------------------------------------------------


def compute_semantic_score(
    resume_text: str,
    jd_text: str,
    alpha: float = 0.6,
) -> float:
    """
    Compute a composite similarity score (0–100) between a resume and a
    job description using dense semantic embeddings.

    The final score blends **semantic similarity** (embedding cosine) with
    a **lexical similarity** heuristic derived from token overlap:

        score = alpha × semantic + (1 - alpha) × lexical

    Both components are scaled to 0–100 before blending.

    Parameters
    ----------
    resume_text:
        Full text of the resume.
    jd_text:
        Full text of the job description.
    alpha:
        Weight for the semantic component.  ``1.0`` means pure semantic;
        ``0.0`` means pure lexical.  Default is ``0.6``.

    Returns
    -------
    float
        Composite score in the range [0, 100].
    """
    if not resume_text.strip() or not jd_text.strip():
        logger.warning("One of the inputs is empty; returning 0.0")
        return 0.0

    alpha = max(0.0, min(1.0, alpha))

    # --- Semantic component ---
    embeddings = get_embeddings([resume_text, jd_text])
    cosine_sim = compute_cosine_similarity(embeddings[0], embeddings[1])
    # Clamp to [0, 1] (negative similarity treated as 0)
    semantic_score = max(0.0, min(1.0, cosine_sim)) * 100.0

    # --- Lexical component (token overlap) ---
    resume_tokens = set(resume_text.lower().split())
    jd_tokens = set(jd_text.lower().split())
    if jd_tokens:
        lexical_score = len(resume_tokens & jd_tokens) / len(jd_tokens) * 100.0
    else:
        lexical_score = 0.0
    lexical_score = min(lexical_score, 100.0)

    # --- Blend ---
    composite = alpha * semantic_score + (1.0 - alpha) * lexical_score
    composite = round(max(0.0, min(100.0, composite)), 2)

    logger.info(
        "Semantic=%.2f  Lexical=%.2f  α=%.2f  → Composite=%.2f",
        semantic_score,
        lexical_score,
        alpha,
        composite,
    )
    return composite

# refactor: improve docstrings for cosine similarity calculation
