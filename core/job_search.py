"""Multi-source job search aggregator for the Job Finder feature."""

import logging
import re
import urllib.request
import urllib.parse
import json
from dataclasses import dataclass, field
from typing import List, Optional
import os

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    description: str
    url: str
    salary: str = "Not disclosed"
    source: str = ""
    posted_date: str = ""
    job_type: str = "Full-time"
    tags: List[str] = field(default_factory=list)
    remote: bool = False


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common HTML entities."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]*>', ' ', text)
    # Decode basic entities
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    # Clean whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _fetch_json(url: str, headers: Optional[dict] = None, timeout: int = 10) -> dict:
    """Fetch JSON data from a URL using urllib.request."""
    if headers is None:
        headers = {}
    
    # Add a standard user agent to avoid blocking
    if "User-Agent" not in headers:
        headers["User-Agent"] = "PSI-Resume-Analyser/1.0"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
            else:
                logger.warning("Failed to fetch JSON from %s, status code: %d", url, response.status)
    except Exception as e:
        logger.warning("Error fetching JSON from %s: %s", url, str(e))
    return {}


def _search_remotive(query: str, category: str = "") -> List[JobListing]:
    """Search remote jobs using the Remotive API."""
    base_url = "https://remotive.com/api/remote-jobs"
    params = {"limit": 20}
    if query:
        params["search"] = query
    if category:
        params["category"] = category
        
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    data = _fetch_json(url)
    
    jobs = []
    if not data or "jobs" not in data:
        return jobs
        
    for j in data["jobs"]:
        title = j.get("title", "")
        company = j.get("company_name", "")
        location = j.get("candidate_required_location", "Remote")
        desc = _strip_html(j.get("description", ""))
        job_url = j.get("url", "")
        salary = j.get("salary", "") or "Not disclosed"
        posted = j.get("publication_date", "")
        # Format posted date to simple YYYY-MM-DD if ISO format
        if posted and len(posted) >= 10:
            posted = posted[:10]
            
        tags = j.get("tags", [])
        j_type = j.get("job_type", "Full-time")
        
        jobs.append(JobListing(
            title=title,
            company=company,
            location=location,
            description=desc,
            url=job_url,
            salary=salary,
            source="Remotive",
            posted_date=posted,
            job_type=j_type,
            tags=tags,
            remote=True
        ))
    return jobs


def _search_arbeitnow(query: str) -> List[JobListing]:
    """Search jobs using the Arbeitnow API (focuses on EU & remote jobs)."""
    # Arbeitnow doesn't have a direct search query parameter in their public API URL,
    # so we fetch the latest jobs and filter client-side.
    url = "https://www.arbeitnow.com/api/job-board-api"
    data = _fetch_json(url)
    
    jobs = []
    if not data or "data" not in data:
        return jobs
        
    keywords = [kw.lower() for kw in query.split()] if query else []
    
    for j in data["data"]:
        title = j.get("title", "")
        company = j.get("company_name", "")
        location = j.get("location", "")
        desc = _strip_html(j.get("description", ""))
        job_url = j.get("url", "")
        tags = j.get("tags", [])
        posted = j.get("created_at", "")
        if posted and len(posted) >= 10:
            posted = posted[:10]
            
        is_remote = j.get("remote", False)
        
        # Client-side filtering if query keywords are provided
        if keywords:
            search_text = f"{title} {desc} {' '.join(tags)}".lower()
            if not any(kw in search_text for kw in keywords):
                continue
                
        jobs.append(JobListing(
            title=title,
            company=company,
            location=location,
            description=desc,
            url=job_url,
            salary="Not disclosed", # Arbeitnow API doesn't standardly expose salary in list API
            source="Arbeitnow",
            posted_date=posted,
            job_type="Full-time",
            tags=tags,
            remote=is_remote
        ))
    return jobs


def _search_adzuna(query: str, country: str = "us") -> List[JobListing]:
    """Search jobs using the Adzuna API (requires API keys)."""
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    
    if not app_id or not app_key:
        return []
        
    base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 20,
    }
    if query:
        params["what"] = query
        
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    data = _fetch_json(url)
    
    jobs = []
    if not data or "results" not in data:
        return jobs
        
    for j in data["results"]:
        title = _strip_html(j.get("title", ""))
        company = j.get("company", {}).get("display_name", "")
        location = j.get("location", {}).get("display_name", "")
        desc = _strip_html(j.get("description", ""))
        job_url = j.get("redirect_url", "")
        
        sal_min = j.get("salary_min")
        sal_max = j.get("salary_max")
        if sal_min and sal_max:
            salary = f"${sal_min:,.0f} - ${sal_max:,.0f}"
        elif sal_min:
            salary = f"${sal_min:,.0f}+"
        else:
            salary = "Not disclosed"
            
        posted = j.get("created", "")
        if posted and len(posted) >= 10:
            posted = posted[:10]
            
        tags = []
        category = j.get("category", {}).get("tag", "")
        if category:
            tags.append(category.replace("_", " ").title())
            
        # Check if remote in title/desc/location
        is_remote = any(term in (title + desc + location).lower() for term in ["remote", "work from home", "telecommute"])
        
        jobs.append(JobListing(
            title=title,
            company=company,
            location=location,
            description=desc,
            url=job_url,
            salary=salary,
            source="Adzuna",
            posted_date=posted,
            job_type="Full-time",
            tags=tags,
            remote=is_remote
        ))
    return jobs


def _deduplicate_jobs(jobs: List[JobListing]) -> List[JobListing]:
    """Deduplicate job listings based on title and company (case-insensitive)."""
    seen = set()
    deduped = []
    for j in jobs:
        key = (j.title.lower().strip(), j.company.lower().strip())
        if key not in seen:
            seen.add(key)
            deduped.append(j)
    return deduped


def search_jobs(
    queries: List[str], 
    location: str = "", 
    remote_only: bool = False, 
    max_results: int = 50
) -> List[JobListing]:
    """Search for jobs across multiple job search engines."""
    all_jobs = []
    
    # Run searches for each query string
    for q in queries:
        q = q.strip()
        if not q:
            continue
            
        logger.info("Searching job boards for query: '%s'", q)
        
        # 1. Remotive (Remote-only)
        try:
            remotive_jobs = _search_remotive(q)
            all_jobs.extend(remotive_jobs)
        except Exception as e:
            logger.warning("Error running Remotive search: %s", str(e))
            
        # 2. Arbeitnow (EU/Worldwide & Remote)
        try:
            arbeitnow_jobs = _search_arbeitnow(q)
            all_jobs.extend(arbeitnow_jobs)
        except Exception as e:
            logger.warning("Error running Arbeitnow search: %s", str(e))
            
        # 3. Adzuna (Global - if API key configured)
        country = os.getenv("ADZUNA_COUNTRY", "us")
        try:
            adzuna_jobs = _search_adzuna(q, country=country)
            all_jobs.extend(adzuna_jobs)
        except Exception as e:
            logger.warning("Error running Adzuna search: %s", str(e))

    # Deduplicate before applying location filters
    unique_jobs = _deduplicate_jobs(all_jobs)
    
    # Apply filters
    filtered_jobs = []
    for j in unique_jobs:
        # Remote only filter
        if remote_only and not j.remote:
            continue
            
        # Location filter
        if location and location.lower().strip() != "remote":
            loc_str = location.lower().strip()
            # If the job isn't remote and doesn't match location, skip
            if not (loc_str in j.location.lower() or (j.remote and "remote" in loc_str)):
                continue
                
        filtered_jobs.append(j)
        
    logger.info("Found %d unique jobs after filtering", len(filtered_jobs))
    return filtered_jobs[:max_results]
