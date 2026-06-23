"""Lightweight File-Based Model Registry and Governance for PSI Resume Analyser."""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

REGISTRY_FILE = os.path.join("data", "model_registry.json")

class ModelRegistry:
    """Manages model information, lifecycle stages, and metadata."""

    _defaults: Dict[str, Dict[str, Any]] = {
        "resume_parser": {
            "name": "gemini-1.5-flash",
            "version": "1.0.0",
            "provider": "Google",
            "capabilities": ["JSON extraction", "Zero-shot parsing"],
            "compliance_tags": ["EEOC-safe", "PII-sensitive-handled"],
            "lifecycle_stage": "production",
            "updated_at": "2026-06-23T00:00:00Z"
        },
        "jd_extractor": {
            "name": "gemini-1.5-flash",
            "version": "1.0.0",
            "provider": "Google",
            "capabilities": ["JSON extraction", "Requirement taxonomy extraction"],
            "compliance_tags": ["EEOC-safe"],
            "lifecycle_stage": "production",
            "updated_at": "2026-06-23T00:00:00Z"
        },
        "skill_normalizer": {
            "name": "gemini-1.5-flash",
            "version": "1.0.0",
            "provider": "Google",
            "capabilities": ["Taxonomy matching", "Semantic clustering"],
            "compliance_tags": ["EEOC-safe"],
            "lifecycle_stage": "production",
            "updated_at": "2026-06-23T00:00:00Z"
        },
        "scorer": {
            "name": "gemini-1.5-flash",
            "version": "1.0.0",
            "provider": "Google",
            "capabilities": ["Composite scoring", "Alignment validation"],
            "compliance_tags": ["EEOC-safe", "Bias-mitigated"],
            "lifecycle_stage": "production",
            "updated_at": "2026-06-23T00:00:00Z"
        },
        "improver": {
            "name": "gemini-1.5-flash",
            "version": "1.0.0",
            "provider": "Google",
            "capabilities": ["STAR framework optimization", "Action-verb rewrite"],
            "compliance_tags": ["EEOC-safe"],
            "lifecycle_stage": "production",
            "updated_at": "2026-06-23T00:00:00Z"
        }
    }

    _cached_models: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def _load_registry(cls) -> Dict[str, Dict[str, Any]]:
        if cls._cached_models is not None:
            return cls._cached_models

        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)

        if not os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                    json.dump(cls._defaults, f, indent=2, ensure_ascii=False)
                logger.info("Initialized model registry file at %s", REGISTRY_FILE)
            except Exception as e:
                logger.error("Failed to write model registry: %s", e)
            cls._cached_models = cls._defaults.copy()
            return cls._cached_models

        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                cls._cached_models = json.load(f)
                return cls._cached_models
        except Exception as e:
            logger.error("Failed to read model registry from %s: %s", REGISTRY_FILE, e)
            return cls._defaults

    @classmethod
    def _save_registry(cls):
        if cls._cached_models is None:
            return
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        try:
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._cached_models, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save model registry: %s", e)

    @classmethod
    def get_model_info(cls, agent_role: str) -> Optional[Dict[str, Any]]:
        """Retrieve model metadata for a given agent/component role."""
        registry = cls._load_registry()
        return registry.get(agent_role)

    @classmethod
    def register_model(cls, agent_role: str, name: str, version: str, provider: str, capabilities: List[str], compliance_tags: List[str], lifecycle_stage: str = "development"):
        """Register or update a model in the registry."""
        registry = cls._load_registry()
        registry[agent_role] = {
            "name": name,
            "version": version,
            "provider": provider,
            "capabilities": capabilities,
            "compliance_tags": compliance_tags,
            "lifecycle_stage": lifecycle_stage,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        cls._cached_models = registry
        cls._save_registry()
        logger.info("Registered model '%s' for role '%s'", name, agent_role)

    @classmethod
    def update_lifecycle(cls, agent_role: str, stage: str):
        """Update the lifecycle stage (development, staging, production, archived) of a model."""
        registry = cls._load_registry()
        if agent_role not in registry:
            raise KeyError(f"Agent role '{agent_role}' not found in model registry.")
        
        valid_stages = ["development", "staging", "production", "archived"]
        if stage not in valid_stages:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of {valid_stages}")

        registry[agent_role]["lifecycle_stage"] = stage
        registry[agent_role]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        cls._cached_models = registry
        cls._save_registry()
        logger.info("Updated lifecycle stage of role '%s' to '%s'", agent_role, stage)

    @classmethod
    def generate_model_card(cls, agent_role: str) -> str:
        """Generate a Markdown Model Card for governance and auditing."""
        info = cls.get_model_info(agent_role)
        if not info:
            return f"# Model Card Not Found\n\nNo model registered for role: `{agent_role}`"

        # Safe join of capabilities
        caps = "\n".join(f"- {cap}" for cap in info.get("capabilities", []))
        
        card = f"""# Model Card: {agent_role.replace('_', ' ').title()}

## Model Specifications
- **Model Name**: {info.get('name', 'N/A')}
- **Version**: {info.get('version', 'N/A')}
- **Provider**: {info.get('provider', 'N/A')}
- **Lifecycle Stage**: `{info.get('lifecycle_stage', 'development')}`
- **Last Updated**: {info.get('updated_at', 'N/A')}

## Capabilities
{caps}

## Compliance & Governance
- **EEOC Bias Mitigation**: {'Verified' if 'EEOC-safe' in info.get('compliance_tags', []) else 'Pending Evaluation'}
- **Data Privacy (PII)**: {'PII-Handled/Masked' if any('PII' in tag for tag in info.get('compliance_tags', [])) else 'General Processing'}
- **Tags**: {', '.join(info.get('compliance_tags', []))}
"""
        return card
