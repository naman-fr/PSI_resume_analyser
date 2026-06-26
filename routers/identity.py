import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.identity_engine import identity_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/identity", tags=["AI Identity & Privacy"])

class TelemetryPayload(BaseModel):
    session_id: str
    mouse_speed: float
    click_rate: float
    typing_speed: float
    error_rate: float
    session_duration: float
    browser_hash: str

class ConsentPayload(BaseModel):
    user_id: str
    analytics: bool
    performance: bool
    marketing: bool
    ai_personalization: bool
    interview_memory: bool
    voice_storage: bool

# Simple in-memory consent store for demo purposes
# In production, this goes to MongoDB
CONSENT_STORE = {}

@router.post("/telemetry")
async def ingest_telemetry(payload: TelemetryPayload):
    """
    Ingests biometric and session telemetry, runs it through ML models (Isolation Forest / KMeans),
    and returns a computed Risk Score and Behavioral Cluster.
    """
    try:
        data = payload.dict()
        result = identity_engine.ingest_telemetry(payload.session_id, data)
        return {
            "success": True,
            "risk_score": result["risk_score"],
            "is_bot": result["is_bot"],
            "user_cluster": result["user_cluster"],
            "action": "BLOCK" if result["is_bot"] else "ALLOW"
        }
    except Exception as e:
        logger.error(f"Telemetry ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/consent")
async def update_consent(payload: ConsentPayload):
    """
    Updates the user's granular AI Data Governance settings.
    """
    CONSENT_STORE[payload.user_id] = payload.dict()
    logger.info(f"Updated AI Consent for {payload.user_id}: {payload.dict()}")
    return {"success": True, "message": "Privacy Preferences Saved"}

@router.get("/consent/{user_id}")
async def get_consent(user_id: str):
    """
    Retrieves the user's AI Data Governance settings.
    """
    if user_id in CONSENT_STORE:
        return {"success": True, "consent": CONSENT_STORE[user_id]}
    return {
        "success": True, 
        "consent": {
            "analytics": True,
            "performance": True,
            "marketing": False,
            "ai_personalization": True,
            "interview_memory": True,
            "voice_storage": False
        }
    }
