import base64
import numpy as np
import logging

logger = logging.getLogger(__name__)

# To avoid crashing environments that don't have these installed yet
try:
    import cv2
    import mediapipe.python.solutions.face_mesh as mp_face_mesh
    
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=2,  # Important for detecting multiple people
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    HAS_CV = True
except ImportError:
    HAS_CV = False
    logger.warning("OpenCV or MediaPipe not installed. Proctoring Engine will run in mock mode.")

class VisionProctor:
    def __init__(self):
        self.enabled = HAS_CV

    def process_frame(self, base64_img: str) -> dict:
        """
        Takes a base64 encoded jpeg/png from WebRTC/WebSocket.
        Returns a dict of alerts (e.g., {"multiple_people": True, "looking_away": False})
        """
        if not self.enabled:
            # Mock mode
            return {"status": "mock", "alerts": []}
            
        try:
            # Decode base64
            encoded_data = base64_img.split(',')[1] if ',' in base64_img else base64_img
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"error": "Invalid image"}

            # Process with MediaPipe
            rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_image)
            
            alerts = []
            
            if not results.multi_face_landmarks:
                alerts.append("CANDIDATE_NOT_DETECTED")
            else:
                num_faces = len(results.multi_face_landmarks)
                if num_faces > 1:
                    alerts.append(f"MULTIPLE_PEOPLE_DETECTED ({num_faces})")
                
                face_landmarks = results.multi_face_landmarks[0]
                
                # Head Pose / Gaze Tracking
                nose_tip = face_landmarks.landmark[1]
                left_eye_inner = face_landmarks.landmark[133]
                right_eye_inner = face_landmarks.landmark[362]
                
                # Check if head is turned drastically
                if nose_tip.x < 0.35 or nose_tip.x > 0.65:
                    alerts.append("HEAD_TURNED_AWAY")
                    
                # Basic Iris/Gaze tracking proxy (are eyes looking away?)
                eye_center_x = (left_eye_inner.x + right_eye_inner.x) / 2.0
                if abs(nose_tip.x - eye_center_x) > 0.1:
                    alerts.append("SUSPICIOUS_GAZE_DETECTED")

                # Very basic "Screen in background" proxy via brightness
                gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
                if np.mean(gray) > 200:
                    alerts.append("HIGH_BACKGROUND_GLARE_SCREEN_DETECTED")

            return {
                "status": "success",
                "face_count": len(results.multi_face_landmarks) if results.multi_face_landmarks else 0,
                "alerts": alerts
            }
            
        except Exception as e:
            logger.error(f"Vision Engine Error: {e}")
            return {"error": str(e)}

vision_proctor = VisionProctor()
