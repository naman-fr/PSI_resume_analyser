"""Version-controlled Prompt Registry for PSI Resume Analyser."""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.prompts import (
    RESUME_PARSER_PROMPT,
    JD_EXTRACTOR_PROMPT,
    SKILL_NORMALIZER_PROMPT,
    SCORER_PROMPT,
    IMPROVER_PROMPT
)

logger = logging.getLogger(__name__)

REGISTRY_FILE = os.path.join("data", "prompt_registry.json")

class PromptRegistry:
    """Enterprise Prompt Registry supporting versioning, metadata, and dynamic persistence."""

    # Default prompts used to initialize the file-backed store
    _defaults: Dict[str, Dict[str, Dict[str, Any]]] = {
        "resume_parser": {
            "v1.0.0": {
                "content": RESUME_PARSER_PROMPT,
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Extract structured JSON from resume PDF text",
                "tags": ["parser", "resume"]
            }
        },
        "jd_extractor": {
            "v1.0.0": {
                "content": JD_EXTRACTOR_PROMPT,
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Extract structured details from Job Description text",
                "tags": ["extractor", "jd"]
            }
        },
        "skill_normalizer": {
            "v1.0.0": {
                "content": SKILL_NORMALIZER_PROMPT,
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Normalize skills against taxonomy standard",
                "tags": ["taxonomy", "skills"]
            }
        },
        "scorer": {
            "v1.0.0": {
                "content": SCORER_PROMPT,
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Score a resume alignment against a job description",
                "tags": ["scoring", "evaluation"]
            }
        },
        "improver": {
            "v1.0.0": {
                "content": IMPROVER_PROMPT,
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Optimize resume bullets using STAR framework",
                "tags": ["improver", "resume"]
            }
        },
        "critic": {
            "v1.0.0": {
                "content": """You are an expert Enterprise AI Critic and Evaluator. Your task is to review the structured extraction outputs from the Resume Parser and JD Extractor.
Validate that the parsed JSON output is accurate, non-hallucinated, conforms to requirements, and has no critical missing sections (e.g. empty lists of skills or experience, or missing applicant name).

Evaluate the extraction quality and output a JSON dictionary containing:
1. "is_valid": boolean (true if the extraction contains sufficient details and no obvious formatting errors)
2. "confidence_score": float (from 0.0 to 1.0)
3. "feedback_details": string (if invalid, specify what fields require re-parsing or correction; otherwise empty string "")

Input under review:
- Parsed Resume: {resume_parsed}
- Extracted JD: {jd_extracted}

Response format: ONLY output raw JSON. Do not include any explanations or markdown fences.""",
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Evaluate parsed output validation and confidence",
                "tags": ["evaluation", "critic"]
            }
        },
        "planner": {
            "v1.0.0": {
                "content": """You are the Lead AI Orchestrator and Planner. Your task is to analyze the candidate's resume text and the job description, and create an adaptive task execution plan.
Break down the key focus areas, identify domain specificity (e.g. Finance, Healthcare, Software Engineering), and direct the multi-agent pipeline.

Output a JSON dictionary containing:
1. "plan_steps": list of strings (ordered list of execution phases)
2. "focus_areas": list of strings (specific domains or critical requirements to prioritize)
3. "targeted_version": string (default "v1.0.0")

Input Resume Context:
{resume_text}

Input JD Context:
{jd_text}

Response format: ONLY output raw JSON. Do not include any explanations or markdown fences.""",
                "author": "system",
                "created_at": "2026-06-23T00:00:00Z",
                "description": "Generate adaptive task execution plan for multi-agent pipeline",
                "tags": ["planner", "orchestrator"]
            }
        }
    }

    _cached_prompts: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None

    @classmethod
    def _load_registry(cls) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Loads prompt registry from local JSON file or initializes with defaults."""
        if cls._cached_prompts is not None:
            return cls._cached_prompts

        # Make sure directory exists
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)

        if not os.path.exists(REGISTRY_FILE):
            # Save defaults to file
            try:
                with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                    json.dump(cls._defaults, f, indent=2, ensure_ascii=False)
                logger.info("Initialized file-backed prompt registry at %s", REGISTRY_FILE)
            except Exception as e:
                logger.error("Failed to write default prompt registry: %s", e)
            cls._cached_prompts = cls._defaults.copy()
            return cls._cached_prompts

        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cached_prompts = data
                logger.info("Successfully loaded prompt registry from %s", REGISTRY_FILE)
                return cls._cached_prompts
        except Exception as e:
            logger.error("Failed to read prompt registry from %s. Using default prompts. Error: %s", REGISTRY_FILE, e)
            return cls._defaults

    @classmethod
    def _save_registry(cls):
        """Saves current prompts to file."""
        if cls._cached_prompts is None:
            return
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        try:
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._cached_prompts, f, indent=2, ensure_ascii=False)
            logger.info("Saved prompt registry to %s", REGISTRY_FILE)
        except Exception as e:
            logger.error("Failed to save prompt registry: %s", e)

    @classmethod
    def get_prompt(cls, key: str, version: str = "v1.0.0") -> str:
        """Retrieve a specific prompt template by name and version."""
        prompts = cls._load_registry()
        if key not in prompts:
            raise KeyError(f"Prompt key '{key}' not found in registry.")

        versions = prompts[key]
        if version not in versions:
            logger.warning(
                "Prompt version '%s' not found for key '%s'. Falling back to 'v1.0.0'.",
                version,
                key
            )
            version = "v1.0.0"

        if version not in versions:
            raise KeyError(f"Version '{version}' and default 'v1.0.0' not found for prompt '{key}'.")

        return versions[version]["content"]

    @classmethod
    def get_prompt_history(cls, key: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve the version history and metadata of a specific prompt."""
        prompts = cls._load_registry()
        if key not in prompts:
            raise KeyError(f"Prompt key '{key}' not found in registry.")
        
        history = {}
        for ver, meta in prompts[key].items():
            history[ver] = {
                "author": meta.get("author", "unknown"),
                "created_at": meta.get("created_at", ""),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", [])
            }
        return history

    @classmethod
    def register_prompt(cls, key: str, version: str, content: str, author: str = "system", description: str = "", tags: List[str] = None):
        """Register a new version of a prompt, updating the persistent JSON store."""
        prompts = cls._load_registry()
        if key not in prompts:
            prompts[key] = {}
        
        prompts[key][version] = {
            "content": content,
            "author": author,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "description": description,
            "tags": tags or []
        }
        cls._cached_prompts = prompts
        cls._save_registry()
        logger.info("Registered new version '%s' of prompt '%s'", version, key)
