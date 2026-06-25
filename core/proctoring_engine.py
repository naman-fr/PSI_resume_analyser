import base64
import numpy as np
import logging

logger = logging.getLogger(__name__)

# To avoid crashing environments that don't have these installed yet
try:
    import cv2
    import os
    
    # Use lightweight Haar cascades instead of MediaPipe to save memory on Render Free Tier
    cascPathface = os.path.dirname(cv2.__file__) + "/data/haarcascade_frontalface_default.xml"
    cascPatheyes = os.path.dirname(cv2.__file__) + "/data/haarcascade_eye.xml"
    
    face_cascade = cv2.CascadeClassifier(cascPathface)
    eye_cascade = cv2.CascadeClassifier(cascPatheyes)
    
    HAS_CV = not face_cascade.empty()
except Exception as e:
    HAS_CV = False
    logger.warning(f"Computer Vision disabled. Proctoring Engine will run in mock mode. Reason: {e}")

class VisionProctor:
    def __init__(self):
        self.enabled = HAS_CV

    def process_frame(self, base64_img: str) -> dict:
        """
        Takes a base64 encoded jpeg/png from WebRTC/WebSocket.
        Returns a dict of alerts (e.g., {"multiple_people": True, "looking_away": False})
        """
        if not self.enabled:
            # Mock mode: Simulate alerts occasionally for UI demonstration
            import random
            alerts = []
            rand_val = random.random()
            if rand_val > 0.95:
                alerts.append("MULTIPLE_PEOPLE_DETECTED (2)")
            elif rand_val > 0.90:
                alerts.append("SUSPICIOUS_GAZE_DETECTED")
            elif rand_val > 0.85:
                alerts.append("HEAD_TURNED_AWAY")
                
            return {"status": "mock", "alerts": alerts}
            
        try:
            # Decode base64
            encoded_data = base64_img.split(',')[1] if ',' in base64_img else base64_img
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"error": "Invalid image"}

            # Process with OpenCV Haar Cascades
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            alerts = []
            
            if len(faces) == 0:
                alerts.append("CANDIDATE_NOT_DETECTED")
            else:
                if len(faces) > 1:
                    alerts.append(f"MULTIPLE_PEOPLE_DETECTED ({len(faces)})")
                
                # Assume the largest face is the candidate
                faces_sorted = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
                x, y, w, h = faces_sorted[0]
                roi_gray = gray[y:y+h, x:x+w]
                
                eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10, minSize=(15, 15))
                
                if len(eyes) == 0:
                    alerts.append("EYES_NOT_ON_SCREEN / LOOKING_AWAY")
                    
                # Very basic "Screen in background" proxy via brightness
                if np.mean(gray) > 200:
                    alerts.append("HIGH_BACKGROUND_GLARE_SCREEN_DETECTED")

            return {
                "status": "success",
                "face_count": len(faces),
                "alerts": alerts
            }
            
        except Exception as e:
            logger.error(f"Vision Engine Error: {e}")
            return {"error": str(e)}

vision_proctor = VisionProctor()
