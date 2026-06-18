"""MLOps fine-tuning data collection loop."""

import json
import os
import logging
from typing import Any, Dict
from config.settings import settings

logger = logging.getLogger(__name__)

def log_finetuning_record(resume_text: str, jd_text: str, final_state: Dict[str, Any]) -> bool:
    """Logs the input resume/JD and output scores/parsed payload for LLM fine-tuning.
    
    Parameters
    ----------
    resume_text : str
        The raw resume text.
    jd_text : str
        The job description text.
    final_state : dict
        The final pipeline state containing scoring and parsed results.
        
    Returns
    -------
    bool
        True if successfully logged, False otherwise.
    """
    if not settings.data_loop.enable_data_loop:
        return False
        
    try:
        # Prepare the instruction
        instruction = (
            "You are an expert ATS (Applicant Tracking System) parser and evaluator. "
            "Analyze the candidate's resume and job description to perform compatibility scoring, "
            "identify matching/missing skills, parse experience and education, highlight red/green flags, "
            "and suggest improvement areas."
        )
        
        # Prepare the input
        input_data = {
            "resume_text": resume_text,
            "job_description": jd_text
        }
        
        # Prepare the output: extract relevant results
        output_data = {
            "resume_parsed": final_state.get("resume_parsed", {}),
            "jd_extracted": final_state.get("jd_extracted", {}),
            "skill_match": final_state.get("skill_match", {}),
            "experience_match": final_state.get("experience_match", {}),
            "education_match": final_state.get("education_match", {}),
            "overall_score": final_state.get("overall_score", 0.0),
            "match_score": final_state.get("match_score", 0.0),
            "red_flags": final_state.get("red_flags", []),
            "green_flags": final_state.get("green_flags", []),
            "strengths": final_state.get("strengths", []),
            "gaps": final_state.get("gaps", []),
            "improvement_suggestions": final_state.get("improvement_suggestions", [])
        }
        
        # Combine into instruction-tuning format
        record = {
            "instruction": instruction,
            "input": json.dumps(input_data, ensure_ascii=False),
            "output": json.dumps(output_data, ensure_ascii=False)
        }
        
        # Determine output file path and ensure directory exists
        file_path = settings.data_loop.finetuning_dataset_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write to JSONL
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
        logger.info(f"MLOps: Successfully logged analysis record to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to log fine-tuning record: {e}")
        return False

def get_dataset_size() -> int:
    """Returns the number of records in the fine-tuning dataset."""
    file_path = settings.data_loop.finetuning_dataset_path
    if not os.path.exists(file_path):
        return 0
    try:
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count
    except Exception as e:
        logger.error(f"Failed to read dataset size: {e}")
        return 0
