"""Search query generator for the Job Finder feature."""

import json
import logging
from typing import Dict, List, Any

from config.prompts import PROMPTS
from agents.resume_parser import get_llm, _extract_json

logger = logging.getLogger(__name__)


def _generate_queries_heuristic(resume_parsed: dict) -> dict:
    """Heuristic fallback for query generation when LLM is unavailable."""
    logger.info("Using heuristic job query generation fallback.")
    
    # 1. Try to get job titles from experience history
    job_titles = []
    experience = resume_parsed.get("experience", [])
    if experience and isinstance(experience, list):
        for exp in experience[:2]:
            if isinstance(exp, dict) and exp.get("title"):
                title = exp["title"].strip()
                if title and title not in job_titles:
                    job_titles.append(title)
                    
    # Add a generic title based on name/skills if no title found
    if not job_titles:
        job_titles.append("Software Engineer")
        job_titles.append("Developer")

    # 2. Extract key skills for search keywords
    skills = resume_parsed.get("skills", [])
    search_keywords = []
    if skills and isinstance(skills, list):
        # Clean skills and take top ones
        clean_skills = [s.strip() for s in skills if s and len(s.strip()) > 1]
        if len(clean_skills) >= 2:
            # Combine 2 skills at a time
            search_keywords.append(" ".join(clean_skills[:2]))
            if len(clean_skills) >= 4:
                search_keywords.append(" ".join(clean_skills[2:4]))
        else:
            search_keywords.append("developer")
    else:
        search_keywords.append("software developer")

    # Ensure we have at least one keyword matching first title
    if job_titles and not any(title.lower() in kw.lower() for title in job_titles for kw in search_keywords):
        search_keywords.insert(0, job_titles[0])

    location = resume_parsed.get("location", "") or "Remote"
    
    return {
        "job_titles": job_titles[:3],
        "search_keywords": search_keywords[:3],
        "target_location": location,
        "experience_level": "mid"
    }


def generate_search_queries(resume_parsed: dict) -> dict:
    """Generate job search queries using LLM with heuristic fallback."""
    if not resume_parsed:
        return _generate_queries_heuristic({})
        
    try:
        llm, provider = get_llm()
        prompt = PROMPTS.get("job_query_generator", "")
        
        # Serialize resume for prompt
        resume_summary = {
            "skills": resume_parsed.get("skills", []),
            "experience": [
                {"title": exp.get("title"), "description": exp.get("description", "")[:100]}
                for exp in resume_parsed.get("experience", [])[:3]
                if isinstance(exp, dict)
            ],
            "location": resume_parsed.get("location", "")
        }
        
        user_message = f"Generate job search queries for this candidate:\n\n{json.dumps(resume_summary, indent=2)}"
        
        logger.info("Requesting LLM-based job query generation...")
        response = llm.invoke([
            ("system", prompt),
            ("user", user_message)
        ])
        
        result = _extract_json(response.content)
        
        # Validate schema
        if not isinstance(result, dict) or "job_titles" not in result or "search_keywords" not in result:
            raise ValueError("Invalid JSON schema returned by LLM")
            
        logger.info("Successfully generated LLM job queries: %s", result)
        return result
        
    except Exception as e:
        logger.warning("LLM query generation failed: %s. Falling back to heuristic.", str(e))
        return _generate_queries_heuristic(resume_parsed)
