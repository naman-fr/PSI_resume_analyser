"""Premium Resume Intelligence Suite Core Implementation."""

import logging
import json
import time
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

def evaluate_ats_integrity(resume_text: str, invisible_text_flagged: bool, invisible_details: dict) -> Dict[str, Any]:
    """Generates the ATS Integrity Analysis report."""
    
    score = 100
    issues = []
    
    # 1. Hidden text check
    if invisible_text_flagged:
        score -= 40
        words = invisible_details.get('detected_words', [])
        issues.append(f"Hidden keyword block found: {', '.join(words[:5])}")
        
    # 2. Keyword stuffing check (basic heuristic)
    word_counts = {}
    for word in resume_text.lower().split():
        if len(word) > 4:
            word_counts[word] = word_counts.get(word, 0) + 1
            
    stuffed_keywords = [w for w, c in word_counts.items() if c > 10 and w not in ["experience", "project", "using", "with", "from"]]
    if stuffed_keywords:
        score -= min(30, len(stuffed_keywords) * 5)
        issues.append(f"Abnormal keyword density detected for: {', '.join(stuffed_keywords[:3])}")
        
    manipulation_risk = "High" if score < 60 else "Medium" if score < 85 else "Low"
    
    return {
        "integrity_score": max(0, score),
        "manipulation_risk": manipulation_risk,
        "keyword_authenticity_score": max(0, score + 5),
        "issues": issues,
        "impact": "This resume may receive inflated ATS scores compared to actual recruiter evaluation." if score < 80 else "Resume appears authentic and free of ATS manipulation."
    }


def evaluate_consistency_index(resume_text: str, link_verification: dict, parsed_data: dict) -> Dict[str, Any]:
    """Generates the Consistency Index based on external links."""
    
    verified = []
    partially_verified = []
    unsupported = []
    
    trust_score = link_verification.get("trust_score", 50)
    urls = link_verification.get("checked_urls", {})
    
    # Simple logic to simulate claim verification
    claims = []
    if parsed_data.get("skills"):
        claims.append(f"Possesses skills: {', '.join(parsed_data['skills'][:3])}")
    if parsed_data.get("experience"):
        claims.append(f"Worked at: {parsed_data['experience'][0].get('company', 'Unknown')}")
        
    has_github = False
    has_linkedin = False
    
    for url, data in urls.items():
        if data.get("type") == "github" and data.get("valid"):
            has_github = True
            repos = data.get("repos", 0)
            if repos > 0:
                verified.append(f"✓ GitHub repository ({url}) confirms technical engagement ({repos} public repos).")
            else:
                partially_verified.append(f"⚠ GitHub profile ({url}) exists but lacks public repository evidence.")
        elif data.get("type") == "linkedin" and data.get("valid"):
            has_linkedin = True
            partially_verified.append(f"⚠ LinkedIn profile ({url}) is active but automated scraping is restricted.")
        elif data.get("valid"):
            verified.append(f"✓ Portfolio ({url}) is live and reachable.")
            
    if not has_github and "GitHub" in resume_text:
        unsupported.append("✗ Claimed GitHub profile link is broken or missing.")
        
    for claim in claims:
        if "github" in claim.lower() and not has_github:
            unsupported.append(f"✗ Claim '{claim}' lacks verifiable repository proof.")
            
    if not verified and not partially_verified:
        unsupported.append("✗ No external verifiable evidence provided for claims.")
        
    index_score = 100
    if unsupported:
        index_score -= len(unsupported) * 15
    if not verified:
        index_score -= 20
        
    return {
        "consistency_index": max(0, min(100, index_score)),
        "verified": verified,
        "partially_verified": partially_verified,
        "unsupported": unsupported
    }


def evaluate_hiring_readiness_and_simulation_llm(parsed_data: dict, match_score: float) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Uses Groq LLM to generate Hiring Readiness and Simulation Engine data."""
    try:
        from agents.resume_parser import get_llm, _extract_json
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm, provider = get_llm()
        
        system_prompt = """You are a Principal AI Tech Recruiter and Engineering Manager evaluating a candidate's resume data.
Your goal is to deeply analyze their experience and output a JSON response containing two objects: "readiness" and "simulation".

For "readiness":
- overall_readiness: (0-100) estimated chance to convert to a phone screen.
- conversion_estimate: "High", "Moderate", or "Low"
- subscores: an object with "software_engineering", "data_science", "product_management" scores (0-100).
- missing_factors: list of 1-3 critical gaps preventing hire.
- roadmap: 1-2 sentence actionable advice to improve.

For "simulation":
- ats_score: exactly the provided ATS Match Score.
- recruiter_score: (0-100) how a human recruiter would score it (focuses on tenure, clarity).
- tech_lead_score: (0-100) how a Tech Lead would score it (focuses on deep technical depth).
- manager_score: (0-100) how a Hiring Manager would score it (focuses on business impact).
- gap_analysis: 1-2 sentence explanation of the score differences.

Return ONLY valid JSON. Do not use markdown wrappers if possible.
{
  "readiness": { ... },
  "simulation": { ... }
}
"""
        user_prompt = f"ATS Match Score: {match_score}\n\nCandidate Data:\n{json.dumps(parsed_data, default=str)[:3000]}"
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        data = _extract_json(response.content)
        
        readiness = data.get("readiness", {})
        simulation = data.get("simulation", {})
        
        # Fallback to ensure basic structure
        if "overall_readiness" not in readiness:
            raise ValueError("Invalid readiness structure")
            
        return readiness, simulation
        
    except Exception as e:
        logger.warning(f"Generative AI Premium Fallback triggered due to error: {e}")
        # Fallback to heuristics
        readiness_score = int(match_score * 0.8)
        readiness = {
            "overall_readiness": readiness_score,
            "conversion_estimate": "Moderate",
            "subscores": {"software_engineering": readiness_score, "data_science": readiness_score, "product_management": readiness_score},
            "missing_factors": ["Could not load AI insights."],
            "roadmap": "Focus on quantifying achievements."
        }
        simulation = {
            "ats_score": int(match_score),
            "recruiter_score": int(match_score * 0.9),
            "tech_lead_score": int(match_score * 0.85),
            "manager_score": int(match_score * 0.88),
            "gap_analysis": "AI simulation unavailable. Showing heuristic fallback."
        }
        return readiness, simulation


def run_premium_intelligence_suite(resume_text: str, parsed_data: dict, final_state: dict) -> dict:
    """Executes all Premium Tier components and attaches them to the final state."""
    
    # Extract prerequisite data from final_state
    invisible_flag = final_state.get("invisible_text_flagged", False)
    invisible_details = final_state.get("invisible_text_details", {})
    links_verif = final_state.get("links_verification", {})
    match_score = final_state.get("match_score", 50.0)
    
    # Run intelligence modules
    integrity = evaluate_ats_integrity(resume_text, invisible_flag, invisible_details)
    consistency = evaluate_consistency_index(resume_text, links_verif, parsed_data)
    
    # LLM Generative AI Call
    readiness, simulation = evaluate_hiring_readiness_and_simulation_llm(parsed_data, match_score)
    
    # Compile Premium Payload
    premium_report = {
        "integrity": integrity,
        "consistency": consistency,
        "readiness": readiness,
        "simulation": simulation,
        "timestamp": time.time()
    }
    
    return premium_report
