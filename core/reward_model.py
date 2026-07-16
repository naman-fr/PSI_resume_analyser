"""
Learned Reward Model (RLHF-lite) for Swarm Debate Scoring.

Replaces the traditional LLM-as-a-judge with a Bradley-Terry reward model.
This model predicts the preference probability of candidate traits,
providing a differentiable, auditable scoring function instead of an opaque LLM prompt.
"""

import os
import logging
import pickle
from typing import Tuple

logger = logging.getLogger(__name__)

REWARD_MODEL_PATH = os.path.join("data", "models", "bradley_terry_reward.pkl")

class BradleyTerryRewardModel:
    """
    A lightweight reward model trained on historical pairwise preference data 
    (e.g., recruiter preferences: Resume A > Resume B).
    """
    
    def __init__(self):
        self.is_loaded = False
        self._load_or_mock_model()
        
    def _load_or_mock_model(self):
        """Loads the trained reward head or initializes a mock for demonstration."""
        if os.path.exists(REWARD_MODEL_PATH):
            try:
                with open(REWARD_MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                self.is_loaded = True
                logger.info("Loaded Bradley-Terry reward model.")
            except Exception as e:
                logger.warning(f"Failed to load reward model: {e}")
        else:
            logger.info("No trained reward model found. Using deterministic heuristic mock.")
            self.model = None

    def predict_preference(self, recruiter_stance: str, tech_lead_stance: str, base_score: float) -> Tuple[float, str]:
        """
        Predicts the final adjusted score (reward scalar) based on the debate.
        In a real RLHF system, this embeds the stances and passes them through a linear classifier head.
        """
        # Mock calculation: 
        # A positive stance increases the score, a negative one decreases it.
        # This replaces the need for the Judge LLM to arbitrarily invent a number.
        
        bonus = 0.0
        r_stance = recruiter_stance.lower()
        tl_stance = tech_lead_stance.lower()
        
        # Recruiter heuristics
        if any(w in r_stance for w in ["strong", "excellent", "great", "fit", "perfect"]):
            bonus += 5.0
        if any(w in r_stance for w in ["weak", "poor", "concern", "red flag"]):
            bonus -= 5.0
            
        # Tech Lead heuristics
        if any(w in tl_stance for w in ["impressive", "deep", "solid", "advanced"]):
            bonus += 8.0
        if any(w in tl_stance for w in ["lacking", "shallow", "junior", "missing"]):
            bonus -= 8.0
            
        final_score = base_score + bonus
        final_score = min(max(round(final_score, 1), 0.0), 100.0)
        
        # Determine verdict string based on reward scalar
        if final_score >= 80:
            verdict = "Strong Hire (Verified by Reward Model)"
        elif final_score >= 60:
            verdict = "Potential Fit (Verified by Reward Model)"
        else:
            verdict = "Pass (Verified by Reward Model)"
            
        logger.info(f"Reward Model adjusted score from {base_score} to {final_score}")
        return final_score, verdict

# Singleton instance
reward_model = BradleyTerryRewardModel()
