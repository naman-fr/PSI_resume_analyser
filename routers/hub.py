import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid

from core.mongo_db import get_db
from core.cache import cache
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

class ResumeSavePayload(BaseModel):
    parsed_json: Dict[str, Any]
    analysis_result: Dict[str, Any]

class InterviewSavePayload(BaseModel):
    duration_seconds: int
    transcript: List[Dict[str, str]]
    final_feedback: str

def _extract_skills_from_analysis(analysis_result: Dict[str, Any]) -> List[str]:
    # Try to extract skills from the AI's analysis JSON
    skills = []
    # E.g., if there's a skill_taxonomy or similar in the result
    return skills

@router.get("/profile")
def get_hub_profile(user_id: str = Depends(get_current_user)):
    """Fetches the complete Candidate Intelligence Hub profile."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    cache_key = f"profile_{user_id}"
    cached_profile = cache.get(cache_key)
    if cached_profile:
        return cached_profile

    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user_doc = db.users.find_one({"user_id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Ensure default arrays exist
    profile_data = {
        "resume_vault": user_doc.get("resume_vault", []),
        "interview_vault": user_doc.get("interview_vault", []),
        "skill_genome": user_doc.get("skill_genome", {}),
        "ai_memory": user_doc.get("ai_memory", {
            "weaknesses": [],
            "strengths": [],
            "learning_style": "unknown"
        }),
        "career_health_score": user_doc.get("career_health_score", 85)
    }
    
    cache.set(cache_key, profile_data, expire_seconds=3600)
    return profile_data


def sync_resume_to_vault(user_id: str, filename: str, resume_text: str, parsed_json: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
    db = get_db()
    if db is None:
        return ""
        
    vault_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": filename,
        "resume_text": resume_text,
        "parsed_data": parsed_json,
        "analysis": analysis_result,
        "overall_score": analysis_result.get("overall_score", 0)
    }
    
    db.users.update_one(
        {"user_id": user_id},
        {"$push": {"resume_vault": vault_entry}}
    )
    
    try:
        from agents.resume_parser import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        import json
        
        llm, provider = get_llm()
        
        prompt = f"""
Extract a skill_genome and ai_memory from this resume.
Format MUST be strictly JSON:
{{
  "skill_genome": {{ "Python": 0.9, "React": 0.8 }},
  "ai_memory": {{ "strengths": ["Strong backend"], "weaknesses": ["No cloud"], "learning_style": "unknown" }}
}}
Resume:
{resume_text[:3000]}
"""
        res = llm.invoke([
            SystemMessage(content="You are a JSON extractor. Return ONLY valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        data = json.loads(content)
        new_genome = data.get("skill_genome", {})
        new_memory = data.get("ai_memory", {})
        
        user_doc = db.users.find_one({"user_id": user_id})
        if user_doc:
            current_genome = user_doc.get("skill_genome", {})
            for k, v in new_genome.items():
                current_genome[k] = max(current_genome.get(k, 0.0), float(v))
                
            current_ai = user_doc.get("ai_memory", {"strengths": [], "weaknesses": [], "learning_style": "unknown"})
            
            db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "skill_genome": current_genome,
                    "ai_memory": {
                        "strengths": list(set(current_ai.get("strengths", []) + new_memory.get("strengths", []))),
                        "weaknesses": list(set(current_ai.get("weaknesses", []) + new_memory.get("weaknesses", []))),
                        "learning_style": new_memory.get("learning_style", current_ai.get("learning_style"))
                    }
                }}
            )
    except Exception as e:
        logger.error(f"Failed to extract genome in sync_resume: {e}")
        
    cache.invalidate(f"profile_{user_id}")
    return vault_entry["id"]

@router.post("/save_resume")
def save_resume_to_vault(payload: ResumeSavePayload, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    vault_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parsed_data": payload.parsed_json,
        "analysis": payload.analysis_result,
        "overall_score": payload.analysis_result.get("overall_score", 0)
    }
    
    # Push to resume vault
    db.users.update_one(
        {"user_id": user_id},
        {"$push": {"resume_vault": vault_entry}}
    )
    
    cache.invalidate(f"profile_{user_id}")
    
    return {"status": "success", "message": "Resume saved to Intelligence Vault"}

@router.post("/save_interview")
def save_interview_to_vault(payload: InterviewSavePayload, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    vault_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration": payload.duration_seconds,
        "transcript": payload.transcript,
        "feedback": payload.final_feedback
    }
    
    # Push to interview vault
    db.users.update_one(
        {"user_id": user_id},
        {"$push": {"interview_vault": vault_entry}}
    )
    
    cache.invalidate(f"profile_{user_id}")
    
    return {"status": "success", "message": "Interview session saved to Vault"}

class IntegrationTogglePayload(BaseModel):
    integration_id: str
    is_connected: bool

@router.get("/integrations")
def get_integrations(user_id: str = Depends(get_current_user)):
    """Fetch connected app integrations."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    cache_key = f"integrations_{user_id}"
    cached_integ = cache.get(cache_key)
    if cached_integ:
        return cached_integ

    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user_doc = db.users.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Default integrations state
    default_integrations = {
        "google_drive": False,
        "google_calendar": False,
        "gmail": False,
        "github": False,
        "notion": False,
        "slack": False,
        "neo4j": False
    }
    
    current_integrations = user_doc.get("integrations", {})
    default_integrations.update(current_integrations)
    
    cache.set(cache_key, default_integrations, expire_seconds=3600)
    return default_integrations

@router.post("/integrations/toggle")
def toggle_integration(payload: IntegrationTogglePayload, user_id: str = Depends(get_current_user)):
    """Toggle connection status of a specific integration."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {f"integrations.{payload.integration_id}": payload.is_connected}}
    )
    
    cache.invalidate(f"integrations_{user_id}")
    
    return {"status": "success", "integration_id": payload.integration_id, "is_connected": payload.is_connected}
