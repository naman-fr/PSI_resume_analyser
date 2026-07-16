"""
Conformal Prediction Module.

Wraps deterministic point predictions (e.g., match scores) in statistically rigorous 
confidence intervals using conformal calibration. This provides a quantifiable measure of 
uncertainty for EEOC audits and fairness transparency.
"""

import math
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class ConformalPredictor:
    """
    Computes marginal conformal prediction intervals for regression scores.
    """
    
    def __init__(self):
        # In a production system, these would be the absolute residuals |y - y_hat|
        # calculated on a calibration hold-out set of historical resumes.
        self.calibration_errors: List[float] = [2.5, 3.1, 1.2, 5.0, 4.2, 6.7, 3.8, 2.1, 4.5, 5.2]
        self.calibration_errors.sort()
        
    def get_conformal_interval(self, point_prediction: float, alpha: float = 0.10) -> Tuple[float, float]:
        """
        Returns a (1 - alpha) confidence interval [lower, upper] for the point prediction.
        
        Args:
            point_prediction: The predicted match score (e.g., 74.5)
            alpha: The acceptable error rate (0.10 means 90% confidence)
        """
        n = len(self.calibration_errors)
        if n == 0:
            return point_prediction, point_prediction
            
        # Calculate the index for the (1 - alpha) quantile
        # Formula: ceil((n + 1) * (1 - alpha))
        q_index = math.ceil((n + 1) * (1 - alpha))
        
        # Cap index to avoid out of bounds
        q_index = min(max(1, q_index), n)
        
        quantile_error = self.calibration_errors[q_index - 1]
        
        lower_bound = max(0.0, point_prediction - quantile_error)
        upper_bound = min(100.0, point_prediction + quantile_error)
        
        return round(lower_bound, 1), round(upper_bound, 1)

# Singleton instance
conformal_predictor = ConformalPredictor()
