import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from agents.interview_state import InterviewState
from agents.interview_graph import interview_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["Interview"])

class InitRequest(BaseModel):
    resume_text: str
    jd_text: str
    focus: Optional[str] = "balanced"

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    interview_tree: List[str]
    current_topic: str
    difficulty_level: int
    evaluations: List[Dict[str, Any]] = []

class ProctorEvent(BaseModel):
    event_type: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None

@router.post("/init")
async def init_interview(req: InitRequest):
    """Phase 1 & 3: Initializes the interview tree and generates the first question."""
    try:
        initial_state: InterviewState = {
            "resume_text": req.resume_text,
            "jd_text": req.jd_text,
            "interview_focus": req.focus,
            "messages": [],
            "evaluations": []
        }
        # Run planner node
        result_state = interview_graph.invoke(initial_state)
        
        return {
            "success": True,
            "interview_tree": result_state.get("interview_tree", []),
            "current_topic": result_state.get("current_topic", ""),
            "difficulty_level": result_state.get("difficulty_level", 5),
            "messages": result_state.get("messages", [])
        }
    except Exception as e:
        logger.error(f"Failed to init interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_interview(req: ChatRequest):
    """Phase 4 & GenAI Feature: Socratic Interview Agent."""
    try:
        current_state: InterviewState = {
            "messages": req.messages,
            "interview_tree": req.interview_tree,
            "current_topic": req.current_topic,
            "difficulty_level": req.difficulty_level,
            "evaluations": req.evaluations,
            "is_complete": False
        }
        
        # Run evaluator -> socratic nodes
        result_state = interview_graph.invoke(current_state)
        
        return {
            "success": True,
            "messages": result_state.get("messages", []),
            "difficulty_level": result_state.get("difficulty_level", req.difficulty_level),
            "evaluations": result_state.get("evaluations", []),
            "is_complete": result_state.get("is_complete", False)
        }
    except Exception as e:
        logger.error(f"Failed to chat interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proctor")
async def log_proctor_event(event: ProctorEvent):
    """Phase 5: Real-Time Proctoring Endpoint (Browser Events)."""
    # In a full production system, we'd append this to a database linked to the session_id
    logger.warning(f"PROCTOR ALERT: {event.event_type} at {event.timestamp}. Details: {event.details}")
    return {"status": "logged", "severity": "warning"}
