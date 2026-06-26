import os
import json
import logging
import numpy as np
from typing import Dict, Any, List
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

SESSION_STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "session_embeddings.json")

class IdentityEngine:
    def __init__(self):
        self.session_history = []
        self._load_history()
        
        # Models
        self.fraud_detector = IsolationForest(contamination=0.05, random_state=42)
        self.clusterer = KMeans(n_clusters=3, random_state=42, n_init=10)
        
        self.is_trained = False
        self._train_models()

    def _load_history(self):
        try:
            if os.path.exists(SESSION_STORE_PATH):
                with open(SESSION_STORE_PATH, "r") as f:
                    self.session_history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session history: {e}")
            self.session_history = []

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(SESSION_STORE_PATH), exist_ok=True)
            with open(SESSION_STORE_PATH, "w") as f:
                json.dump(self.session_history, f)
        except Exception as e:
            logger.error(f"Failed to save session history: {e}")

    def _extract_vector(self, telemetry: Dict[str, Any]) -> List[float]:
        """
        Converts raw telemetry into a continuous vector for ML.
        Expected keys: mouse_speed, click_rate, typing_speed, error_rate, session_duration
        """
        return [
            float(telemetry.get("mouse_speed", 0.0)),
            float(telemetry.get("click_rate", 0.0)),
            float(telemetry.get("typing_speed", 0.0)),
            float(telemetry.get("error_rate", 0.0)),
            float(telemetry.get("session_duration", 0.0))
        ]

    def _train_models(self):
        if len(self.session_history) > 10:
            try:
                X = np.array([self._extract_vector(t) for t in self.session_history])
                # Add some slight noise if all vectors are identical to prevent KMeans/IForest crash
                noise = np.random.normal(0, 0.01, X.shape)
                X = X + noise
                
                self.fraud_detector.fit(X)
                if len(self.session_history) >= 3:
                    self.clusterer.fit(X)
                self.is_trained = True
                logger.info(f"Identity Engine ML models retrained on {len(self.session_history)} sessions.")
            except Exception as e:
                logger.warning(f"ML Training skipped (insufficient variance or error): {e}")
                self.is_trained = False
        else:
            self.is_trained = False

    def ingest_telemetry(self, session_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives real-time telemetry, runs it through the ML pipeline, and returns Risk Score.
        """
        vector = self._extract_vector(telemetry)
        
        # Save to history for continual learning
        telemetry["session_id"] = session_id
        self.session_history.append(telemetry)
        
        # Keep only last 1000 sessions for training memory
        if len(self.session_history) > 1000:
            self.session_history = self.session_history[-1000:]
            
        self._save_history()
        
        # Periodically retrain (simulating continual learning)
        if len(self.session_history) % 5 == 0:
            self._train_models()

        result = {
            "risk_score": 0,
            "is_bot": False,
            "user_cluster": "Unknown"
        }

        # 1. Evaluate Risk (Fraud Detection)
        if self.is_trained:
            X_new = np.array([vector])
            # IF returns 1 for inliers, -1 for outliers
            anomaly_score = self.fraud_detector.decision_function(X_new)[0]
            prediction = self.fraud_detector.predict(X_new)[0]
            
            # Map anomaly_score (approx -0.5 to 0.5) to a 0-100 Risk Score
            # Lower score means more anomalous (higher risk)
            normalized_risk = max(0, min(100, int((0.5 - anomaly_score) * 100)))
            result["risk_score"] = normalized_risk
            
            # If risk > 75 or IF predicts -1, flag as bot
            if prediction == -1 or normalized_risk > 75:
                result["is_bot"] = True
                
            # 2. Assign Persona Cluster
            try:
                cluster = self.clusterer.predict(X_new)[0]
                cluster_names = ["Aggressive/Fast", "Methodical/Slow", "Standard/Average"]
                result["user_cluster"] = cluster_names[cluster % 3]
            except Exception:
                pass
        else:
            # Heuristic fallback before enough data is collected
            if vector[0] > 5000 or vector[1] > 20: # Unrealistic mouse speed or clicks/sec
                result["risk_score"] = 90
                result["is_bot"] = True
            elif vector[0] == 0 and vector[1] == 0 and vector[2] == 0: # Zero telemetry is suspicious
                result["risk_score"] = 60

        return result

# Singleton instance
identity_engine = IdentityEngine()
