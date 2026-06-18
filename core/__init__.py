"""Core processing modules for PSI Resume Analyser."""

from core.pdf_parser import extract_text_from_pdf
from core.embeddings import get_embeddings, get_embedding_model
from core.similarity import compute_cosine_similarity, compute_semantic_score
from core.skill_taxonomy import SkillTaxonomy
from core.job_search import search_jobs, JobListing
from core.job_matcher import score_jobs, ScoredJob
from core.job_query_generator import generate_search_queries
from core.db import init_db

# Initialize application database
init_db()

__all__ = [
    "extract_text_from_pdf",
    "get_embeddings",
    "get_embedding_model",
    "compute_cosine_similarity",
    "compute_semantic_score",
    "SkillTaxonomy",
    "search_jobs",
    "JobListing",
    "score_jobs",
    "ScoredJob",
    "generate_search_queries",
    "init_db",
]


