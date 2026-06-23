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
        if posted:
            posted_str = str(posted)
            if len(posted_str) >= 10:
                posted = posted_str[:10]
            else:
                posted = posted_str
            
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
        if posted:
            posted_str = str(posted)
            if len(posted_str) >= 10:
                posted = posted_str[:10]
            else:
                posted = posted_str
            
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
            salary="Not disclosed",
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
    
    if not app_id or not app_key or "your_adzuna" in app_id:
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
        if posted:
            posted_str = str(posted)
            if len(posted_str) >= 10:
                posted = posted_str[:10]
            else:
                posted = posted_str
            
        tags = []
        category = j.get("category", {}).get("tag", "")
        if category:
            tags.append(category.replace("_", " ").title())
            
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


def _search_jsearch(query: str, location: str = "", remote_only: bool = False) -> List[JobListing]:
    """Search jobs using the JSearch API (LinkedIn, Indeed, Internshala, etc. via RapidAPI)."""
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key or "your_rapidapi_key_here" in api_key:
        return []
        
    base_url = "https://jsearch.p.rapidapi.com/search"
    
    # Construct search query
    search_q = query
    if location:
        search_q = f"{query} in {location}"
        
    params = {
        "query": search_q,
        "num_pages": "1",
        "date_posted": "week"
    }
    
    if remote_only:
        params["remote_jobs_only"] = "true"
        
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    data = _fetch_json(url, headers=headers)
    jobs = []
    if not data or "data" not in data:
        return jobs
        
    for j in data["data"]:
        title = j.get("job_title", "")
        company = j.get("employer_name", "")
        
        city = j.get("job_city", "")
        state = j.get("job_state", "")
        country = j.get("job_country", "")
        location_parts = [p for p in [city, state, country] if p]
        loc = ", ".join(location_parts) if location_parts else "Remote"
        
        desc = _strip_html(j.get("job_description", ""))
        job_url = j.get("job_apply_link", "") or j.get("job_google_link", "")
        
        min_sal = j.get("job_min_salary")
        max_sal = j.get("job_max_salary")
        currency = j.get("job_salary_currency", "USD")
        if min_sal and max_sal:
            salary = f"{currency} {min_sal:,.0f} - {max_sal:,.0f}"
        elif min_sal:
            salary = f"{currency} {min_sal:,.0f}+"
        else:
            salary = "Not disclosed"
            
        posted = j.get("job_posted_at_datetime_utc", "")
        if posted:
            posted_str = str(posted)
            if len(posted_str) >= 10:
                posted = posted_str[:10]
            else:
                posted = posted_str
            
        j_type = j.get("job_employment_type", "Full-time").replace("_", " ").title()
        is_remote = j.get("job_is_remote", False)
        
        tags = []
        if j.get("job_required_skills"):
            tags.extend(j.get("job_required_skills")[:3])
            
        jobs.append(JobListing(
            title=title,
            company=company,
            location=loc,
            description=desc,
            url=job_url,
            salary=salary,
            source="JSearch (LinkedIn/Indeed/Glassdoor)",
            posted_date=posted,
            job_type=j_type,
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
        
        # 1. JSearch (RapidAPI) - Preferred if API Key configured
        api_key = os.getenv("RAPIDAPI_KEY", "")
        if api_key and "your_rapidapi" not in api_key:
            try:
                jsearch_jobs = _search_jsearch(q, location=location, remote_only=remote_only)
                all_jobs.extend(jsearch_jobs)
            except Exception as e:
                logger.warning("Error running JSearch search: %s", str(e))
        
        # 2. Remotive (Remote-only)
        try:
            remotive_jobs = _search_remotive(q)
            all_jobs.extend(remotive_jobs)
        except Exception as e:
            logger.warning("Error running Remotive search: %s", str(e))
            
        # 3. Arbeitnow (EU/Worldwide & Remote)
        try:
            arbeitnow_jobs = _search_arbeitnow(q)
            all_jobs.extend(arbeitnow_jobs)
        except Exception as e:
            logger.warning("Error running Arbeitnow search: %s", str(e))
            
        # 4. Adzuna (Global - if API key configured)
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
            
        # Location filter - only apply if the job is NOT remote
        if location and location.lower().strip() != "remote" and not j.remote:
            loc_str = location.lower().strip()
            # Split candidate location (e.g. "Jaipur, India" -> ["jaipur", "india"]) to see if any matches
            candidate_locs = [part.strip().lower() for part in loc_str.split(",") if part.strip()]
            job_loc_lower = j.location.lower()
            if not any(part in job_loc_lower for part in candidate_locs):
                continue
                
        filtered_jobs.append(j)
        
    logger.info("Found %d unique jobs after filtering", len(filtered_jobs))
    return filtered_jobs[:max_results]
