"""
Continuous Knowledge Distillation (RAD)
Simulates an automated pipeline where the "Teacher Model" (the current large Groq model)
generates high-quality synthetic labels to train a future lightweight "Student Model" (PSI-ProctorNet).
"""
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DISTILLATION_FILE = os.path.join(DATA_DIR, "synthetic_dataset.jsonl")

def extract_knowledge_for_distillation(state: Dict[str, Any]):
    """
    Extracts high-quality reasoning paths from the current session and appends
    them to a local JSONL file for future model fine-tuning.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        evals = state.get("evaluations", [])
        
        # Only distill knowledge from high-scoring evaluations (e.g. score >= 8)
        # This ensures the student model only learns from the best reasoning.
        high_quality_pairs = [e for e in evals if e.get("scores", {}).get("correctness", 0) >= 8]
        
        if not high_quality_pairs:
            return
            
        logger.info(f"Distilling {len(high_quality_pairs)} high-quality pairs for synthetic dataset...")
        
        with open(DISTILLATION_FILE, "a", encoding="utf-8") as f:
            for pair in high_quality_pairs:
                distillation_record = {
                    "instruction": pair.get("question"),
                    "input": pair.get("answer"),
                    "output_score": pair.get("scores")
                }
                f.write(json.dumps(distillation_record) + "\n")
                
    except Exception as e:
        logger.error(f"Knowledge distillation failed: {e}")
