import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.proctoring_engine import vision_proctor

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
                # Process the frame via MediaPipe
                results = vision_proctor.process_frame(frame_base64)
                
                # If there are alerts, immediately send them back to the frontend
                if results.get("alerts"):
                    await websocket.send_json({
                        "type": "proctor_alert",
                        "alerts": results["alerts"]
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
