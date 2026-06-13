"""Job-resume matching engine for the Job Finder feature."""

import logging
from dataclasses import dataclass, field
from typing import List, Tuple
import re

from core.similarity import compute_semantic_score, compute_keyword_overlap
from core.skill_taxonomy import SkillTaxonomy
from core.job_search import JobListing

logger = logging.getLogger(__name__)


@dataclass
class ScoredJob:
    listing: JobListing
    match_score: float = 0.0
    semantic_score: float = 0.0
    skill_overlap: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    category: str = ""


def _categorize(score: float) -> str:
    """Categorize a job match score."""
    if score >= 60.0:
        return "🏆 Top Applicant"
    elif score >= 40.0:
        return "💪 Strong Match"
    elif score >= 20.0:
        return "🎯 Worth Trying"
    return "💼 Decent Match"


def _extract_skills_from_job(job: JobListing, taxonomy: SkillTaxonomy) -> List[str]:
    """Extract and normalize skills from a job listing's tags and description."""
    skills = set()
    
    # 1. Add tags
    for tag in job.tags:
        norm = taxonomy.normalize(tag)
        if norm:
            skills.add(norm.lower())
        else:
            skills.add(tag.lower())
            
    # 2. Extract from first 1000 characters of the description
    desc_part = job.description[:1000]
    # Simple word tokenization to match with taxonomy
    words = re.findall(r'\b[a-zA-Z0-9+#.-]+\b', desc_part)
    
    # Check taxonomy matches
    for w in words:
        if len(w) > 1:
            norm = taxonomy.normalize(w)
            if norm:
                skills.add(norm.lower())
                
    return sorted(list(skills))


def score_jobs(
    resume_text: str,
    resume_skills: List[str],
    jobs: List[JobListing],
    min_score: float = 0.0
) -> List[ScoredJob]:
    """Score and rank job listings against the candidate's resume."""
    scored_jobs = []
    taxonomy = SkillTaxonomy()
    
    # Pre-normalize resume skills
    normalized_resume_skills = []
    for s in resume_skills:
        norm = taxonomy.normalize(s)
        normalized_resume_skills.append((norm or s).lower())
        
    for job in jobs:
        try:
            # 1. Semantic Match
            # Limit description length to avoid slowing down embeddings too much
            desc_for_match = job.description[:1200]
            sem_score = compute_semantic_score(resume_text, desc_for_match)
            
            # 2. Skill Overlap
            job_skills = _extract_skills_from_job(job, taxonomy)
            overlap_res = compute_keyword_overlap(normalized_resume_skills, job_skills)
            
            overlap_pct = overlap_res.get("overlap_percentage", 0.0)
            matched = overlap_res.get("matched_skills", [])
            missing = overlap_res.get("missing_skills", [])
            
            # 3. Composite Score (55% Semantic, 45% Skill Overlap)
            composite_score = 0.55 * sem_score + 0.45 * overlap_pct
            
            # Ensure boundaries
            composite_score = max(0.0, min(100.0, composite_score))
            
            category = _categorize(composite_score)
            if composite_score >= min_score:
                # Retrieve original case names for matching/missing if possible
                scored_jobs.append(ScoredJob(
                    listing=job,
                    match_score=round(composite_score, 1),
                    semantic_score=round(sem_score, 1),
                    skill_overlap=round(overlap_pct, 1),
                    matched_skills=matched,
                    missing_skills=missing[:8], # Limit missing skills display
                    category=category
                ))
        except Exception as e:
            logger.warning("Error scoring job '%s' by '%s': %s", job.title, job.company, str(e))
            
    # Sort descending by composite match score
    scored_jobs.sort(key=lambda x: x.match_score, reverse=True)
    return scored_jobs
