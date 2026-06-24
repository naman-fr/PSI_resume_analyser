"""
MLflow Observability and Evaluation Registry
Tracks prompts, agent decisions, and model versions.
"""
import mlflow
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MLflowTracker:
    def __init__(self, tracking_uri: str = "sqlite:///mlflow.db"):
        self.tracking_uri = tracking_uri
        self.experiment_name = "PSI_Candidate_Scoring"
        
        # Configure MLflow
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            logger.info(f"MLflow initialized. Tracking URI: {self.tracking_uri}")
        except Exception as e:
            logger.warning(f"Could not initialize MLflow: {e}")

    def log_analysis_run(self, resume_id: str, final_state: Dict[str, Any]):
        """Logs the inputs, metrics, and parameters of an agentic analysis run."""
        try:
            with mlflow.start_run(run_name=f"analysis_{resume_id}"):
                # Log Parameters
                mlflow.log_param("premium_mode", final_state.get("premium_mode", False))
                mlflow.log_param("has_invisible_text", final_state.get("invisible_text_flagged", False))
                
                # Log Metrics
                mlflow.log_metric("match_score", final_state.get("match_score", 0.0))
                
                if "premium_report" in final_state:
                    readiness = final_state["premium_report"].get("readiness", {})
                    if "overall_readiness" in readiness:
                        mlflow.log_metric("overall_readiness", readiness["overall_readiness"])
                        
                logger.info(f"Successfully logged run {resume_id} to MLflow.")
        except Exception as e:
            logger.error(f"Failed to log run to MLflow: {e}")

mlflow_tracker = MLflowTracker()
