"""Version-controlled Prompt Registry for PSI Resume Analyser."""

import logging
from typing import Dict

from config.prompts import (
    RESUME_PARSER_PROMPT,
    JD_EXTRACTOR_PROMPT,
    SKILL_NORMALIZER_PROMPT,
    SCORER_PROMPT,
    IMPROVER_PROMPT
)

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Enterprise Prompt Registry supporting versioning and dynamic retrieval."""

    _prompts: Dict[str, Dict[str, str]] = {
        "resume_parser": {
            "v1.0.0": RESUME_PARSER_PROMPT,
        },
        "jd_extractor": {
            "v1.0.0": JD_EXTRACTOR_PROMPT,
        },
        "skill_normalizer": {
            "v1.0.0": SKILL_NORMALIZER_PROMPT,
        },
        "scorer": {
            "v1.0.0": SCORER_PROMPT,
        },
        "improver": {
            "v1.0.0": IMPROVER_PROMPT,
        },
        "critic": {
            "v1.0.0": """\
You are an expert Enterprise AI Critic and Evaluator. Your task is to review the structured extraction outputs from the Resume Parser and JD Extractor.
Validate that the parsed JSON output is accurate, non-hallucinated, conforms to requirements, and has no critical missing sections (e.g. empty lists of skills or experience, or missing applicant name).

Evaluate the extraction quality and output a JSON dictionary containing:
1. "is_valid": boolean (true if the extraction contains sufficient details and no obvious formatting errors)
2. "confidence_score": float (from 0.0 to 1.0)
3. "feedback_details": string (if invalid, specify what fields require re-parsing or correction; otherwise empty string "")

Input under review:
- Parsed Resume: {resume_parsed}
- Extracted JD: {jd_extracted}

Response format: ONLY output raw JSON. Do not include any explanations or markdown fences.
"""
        },
        "planner": {
            "v1.0.0": """\
You are the Lead AI Orchestrator and Planner. Your task is to analyze the candidate's resume text and the job description, and create an adaptive task execution plan.
Break down the key focus areas, identify domain specificity (e.g. Finance, Healthcare, Software Engineering), and direct the multi-agent pipeline.

Output a JSON dictionary containing:
1. "plan_steps": list of strings (ordered list of execution phases)
2. "focus_areas": list of strings (specific domains or critical requirements to prioritize)
3. "targeted_version": string (default "v1.0.0")

Input Resume Context:
{resume_text}

Input JD Context:
{jd_text}

Response format: ONLY output raw JSON. Do not include any explanations or markdown fences.
"""
        }
    }

    @classmethod
    def get_prompt(cls, key: str, version: str = "v1.0.0") -> str:
        """Retrieve a specific prompt template by name and version."""
        if key not in cls._prompts:
            raise KeyError(f"Prompt key '{key}' not found in registry.")

        versions = cls._prompts[key]
        if version not in versions:
            logger.warning(
                "Prompt version '%s' not found for key '%s'. Falling back to 'v1.0.0'.",
                version,
                key
            )
            return versions.get("v1.0.0", "")

        return versions[version]
