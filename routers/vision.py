import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.lvlm_engine import lvlm_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/interview", tags=["Vision Streaming"])

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time video frame ingestion and proctoring.
    The frontend sends base64 encoded frames at a low framerate.
    """
    await websocket.accept()
    session_id = "unknown"
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Extract metadata and frame
            session_id = data.get("session_id", session_id)
            frame_base64 = data.get("frame")
            
            if frame_base64:
                # Process the frame via LVLM for semantic context
                results = lvlm_engine.analyze_multimodal_feed(frame_base64)
                
                # If there are alerts, immediately send them back to the frontend
                if results.get("risk_level") in ["medium", "high"]:
                    await websocket.send_json({
                        "type": "proctor_alert",
                        "alerts": [results["inference"]],
                        "model": results["model_used"]
                    })
                    # In a real system, we'd also log these alerts to the DB for the Final Report
                else:
                    await websocket.send_json({
                        "type": "proctor_status",
                        "status": "clear"
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"Vision stream disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Vision stream error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
