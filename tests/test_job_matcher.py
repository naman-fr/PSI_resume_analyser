"""Tests for job matcher, score boosting, and Star Match categorization."""

import pytest
from core.job_search import JobListing
from core.job_matcher import score_jobs, ScoredJob

def test_score_jobs_boosting_and_star_match():
    # Mock jobs
    job1 = JobListing(
        title="Python Developer",
        company="Startup A",
        location="Remote (Worldwide)",
        description="We are looking for a Python Developer who knows Django, React, PostgreSQL, and Docker.",
        url="http://example.com/1",
        remote=True,
        tags=["python", "django"]
    )
    job2 = JobListing(
        title="Frontend Engineer",
        company="Tech B",
        location="New York, NY",
        description="We need a frontend engineer with React and TypeScript skills.",
        url="http://example.com/2",
        remote=False,
        tags=["react", "typescript"]
    )
    
    # Candidate profile
    resume_text = "I am a Software Engineer with expertise in Python, Django, React, PostgreSQL, and Docker."
    resume_skills = ["Python", "Django", "React", "PostgreSQL", "Docker"]
    
    # Score jobs
    scored = score_jobs(
        resume_text=resume_text,
        resume_skills=resume_skills,
        jobs=[job1, job2],
        min_score=0.0
    )
    
    # We should have exactly 2 jobs returned (fewer than 10 total)
    assert len(scored) == 2
    
    # Check that job1 is marked as "🔥 Star Match"
    assert scored[0].category == "🔥 Star Match"
    # Its score should be boosted to at least 88.0
    assert scored[0].match_score >= 88.0
    
    # Since the max score is boosted/scaled, the top score should be scaled to at least 92.0
    assert scored[0].match_score >= 92.0

def test_score_jobs_ensures_at_least_10():
    # Create 5 matching jobs and 10 completely unrelated jobs (total 15)
    jobs = []
    # 5 matching jobs
    for i in range(5):
        jobs.append(JobListing(
            title=f"Python Django Developer {i}",
            company="Tech Corp",
            location="Remote",
            description="We are seeking a Python Django developer.",
            url=f"http://example.com/match_{i}",
            remote=True
        ))
    # 10 completely unrelated jobs
    for i in range(10):
        jobs.append(JobListing(
            title=f"Gardener {i}",
            company="Garden Inc",
            location="City Y",
            description="Looking for someone to plant flowers and cut grass.",
            url=f"http://example.com/unrelated_{i}",
            remote=False
        ))
        
    resume_text = "Experienced Senior Python Django Developer"
    resume_skills = ["Python", "Django"]
    
    # The 5 matching jobs will have non-zero raw scores and get boosted to >= 92.0.
    # The 10 unrelated jobs will have 0.0 score.
    # When filtering by min_score=35.0, only the 5 matching jobs will pass.
    # Since 5 < 10, the fallback will trigger and return the top 10 jobs.
    scored = score_jobs(
        resume_text=resume_text,
        resume_skills=resume_skills,
        jobs=jobs,
        min_score=35.0
    )
    
    assert len(scored) == 10
