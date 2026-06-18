"""Episodic Memory and Knowledge Graph Engine for PSI Resume Analyser."""

import hashlib
import json
import logging
import os
from typing import Dict, Any, List, Set, Optional

from config.settings import settings
from core.skill_taxonomy import SkillTaxonomy

logger = logging.getLogger(__name__)


class MemoryManager:
    """Enterprise Memory Manager providing Episodic caching and Graph-based taxonomy expansion."""

    _episodic_db: Dict[str, Dict[str, Any]] = {}
    _taxonomy: Optional[SkillTaxonomy] = None

    @classmethod
    def _get_hash(cls, text: str) -> str:
        """Generate a SHA-256 hash of raw input text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @classmethod
    def _ensure_db_loaded(cls) -> None:
        """Load episodic memory from JSON file if enabled."""
        if not settings.memory.enable_long_term_memory:
            return
        
        path = settings.memory.memory_db_path
        if not cls._episodic_db and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cls._episodic_db = json.load(f)
                logger.info("Episodic memory database loaded with %d records.", len(cls._episodic_db))
            except Exception as e:
                logger.error("Failed to load episodic memory database: %s", str(e))

    @classmethod
    def save_parse_to_memory(cls, resume_text: str, parsed_resume: Dict[str, Any]) -> None:
        """Cache a parsed resume in episodic memory to save future API cost and latency."""
        if not settings.memory.enable_long_term_memory:
            return

        cls._ensure_db_loaded()
        resume_hash = cls._get_hash(resume_text)
        cls._episodic_db[resume_hash] = {
            "parsed_resume": parsed_resume,
            "timestamp": time_str() if "time_str" in globals() else "2026-06-18 17:00:00"
        }

        path = settings.memory.memory_db_path
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cls._episodic_db, f, indent=2)
            logger.info("Saved resume parse to episodic memory (Hash: %s).", resume_hash[:10])
        except Exception as e:
            logger.error("Failed to save episodic memory: %s", str(e))

    @classmethod
    def lookup_parse_memory(cls, resume_text: str) -> Optional[Dict[str, Any]]:
        """Look up if this exact resume was parsed before."""
        if not settings.memory.enable_long_term_memory:
            return None

        cls._ensure_db_loaded()
        resume_hash = cls._get_hash(resume_text)
        record = cls._episodic_db.get(resume_hash)
        if record:
            logger.info("Cache Hit: Found resume parse in episodic memory (Hash: %s).", resume_hash[:10])
            return record.get("parsed_resume")
        return None

    @classmethod
    def get_skill_taxonomy(cls) -> SkillTaxonomy:
        """Lazily initialize the SkillTaxonomy instance."""
        if cls._taxonomy is None:
            cls._taxonomy = SkillTaxonomy(settings.memory.skill_graph_path)
        return cls._taxonomy

    @classmethod
    def expand_skills_via_graph(cls, skills: List[str]) -> List[str]:
        """Expand a flat list of skills using parent/sibling links in the taxonomy graph.

        For example, if the candidate has 'PyTorch', we expand to include
        parent 'Deep Learning' or category 'Data Science/ML'.
        """
        if not settings.memory.enable_skill_graph:
            return skills

        taxonomy = cls.get_skill_taxonomy()
        # Initialize taxonomy maps
        taxonomy._ensure_loaded()

        expanded_set: Set[str] = set()
        for s in skills:
            norm_skill = taxonomy.normalize_skill(s)
            expanded_set.add(norm_skill)

            # Find category parent
            lower_norm = norm_skill.lower()
            parent_category = taxonomy._skill_to_category.get(lower_norm)
            if parent_category:
                expanded_set.add(parent_category)
                
                # Fetch sibling skills in the same category (optional logic, let's keep it safe)
                # We can also add secondary keywords to reinforce context matches
                
        return sorted(list(expanded_set))


def time_str() -> str:
    """Helper to return current timestamp string."""
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")
