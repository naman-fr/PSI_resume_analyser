"""
Skill taxonomy module.

Provides a :class:`SkillTaxonomy` that lazily loads a JSON taxonomy file
and exposes helpers for normalising skill names, finding parent categories,
and discovering related (sibling) skills.

Expected JSON schema (``data/skill_taxonomy.json``)::

    {
        "categories": {
            "Programming Languages": {
                "skills": {
                    "Python": {
                        "aliases": ["python3", "python 3", "py"]
                    },
                    "JavaScript": {
                        "aliases": ["js", "ecmascript", "es6"]
                    }
                }
            },
            "Frontend Frameworks": {
                "skills": {
                    "React": {
                        "aliases": ["react.js", "reactjs"]
                    }
                }
            }
        }
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skill_taxonomy.json"


class SkillTaxonomy:
    """
    Hierarchical skill taxonomy with alias-based normalisation.

    Parameters
    ----------
    taxonomy_path:
        Path to the JSON taxonomy file.  Defaults to
        ``<project_root>/data/skill_taxonomy.json``.
    """

    def __init__(self, taxonomy_path: Optional[str | Path] = None) -> None:
        self._taxonomy_path = Path(taxonomy_path) if taxonomy_path else _DEFAULT_TAXONOMY_PATH
        self._loaded = False

        # Populated lazily by _ensure_loaded()
        self._categories: dict[str, dict] = {}
        # Lowered alias → canonical skill name
        self._alias_map: dict[str, str] = {}
        # Canonical skill (lowered) → category name
        self._skill_to_category: dict[str, str] = {}
        # Category name → list of canonical skill names
        self._category_to_skills: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load and index the taxonomy JSON on first use."""
        if self._loaded:
            return

        if not self._taxonomy_path.exists():
            logger.warning(
                "Taxonomy file not found at %s – normalisation will pass through.",
                self._taxonomy_path,
            )
            self._loaded = True
            return

        logger.info("Loading skill taxonomy from %s", self._taxonomy_path)
        with open(self._taxonomy_path, encoding="utf-8") as fh:
            data = json.load(fh)

        # Check if the JSON has "categories" key
        if isinstance(data, dict) and "categories" in data:
            categories_dict = data["categories"]
            is_format_a = True
        else:
            categories_dict = data
            is_format_a = False

        for category_name, category_body in categories_dict.items():
            if not isinstance(category_body, dict):
                continue

            # Extract skills dictionary
            if is_format_a:
                skills = category_body.get("skills", {})
            else:
                skills = category_body

            canonical_names: list[str] = []

            for skill_name, skill_meta in skills.items():
                canonical_names.append(skill_name)
                lower_canonical = skill_name.lower()

                # Map the canonical name itself
                self._alias_map[lower_canonical] = skill_name
                self._skill_to_category[lower_canonical] = category_name

                # Map every alias
                aliases = []
                if isinstance(skill_meta, dict):
                    aliases = skill_meta.get("aliases", [])
                elif isinstance(skill_meta, list):
                    aliases = skill_meta

                for alias in aliases:
                    self._alias_map[alias.strip().lower()] = skill_name

            self._category_to_skills[category_name] = canonical_names

        self._categories = categories_dict
        self._loaded = True
        logger.info(
            "Taxonomy loaded: %d categories, %d canonical skills, %d aliases",
            len(self._category_to_skills),
            sum(len(v) for v in self._category_to_skills.values()),
            len(self._alias_map),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize_skill(self, skill: str) -> str:
        """
        Map a skill string to its canonical name.

        Matching is case-insensitive.  If the skill is not found in the
        taxonomy, the original string is returned unchanged.
        """
        self._ensure_loaded()
        return self._alias_map.get(skill.strip().lower(), skill.strip())

    def normalize(self, skill: str) -> Optional[str]:
        """
        Map a skill string to its canonical name.

        Matching is case-insensitive. Returns None if the skill is not found
        in the taxonomy.
        """
        self._ensure_loaded()
        return self._alias_map.get(skill.strip().lower(), None)

    def get_parent_skill(self, skill: str) -> str:
        """
        Return the parent category for *skill*.

        Falls back to ``"Unknown"`` when the skill is not in the taxonomy.
        """
        self._ensure_loaded()
        canonical = self.normalize_skill(skill)
        return self._skill_to_category.get(canonical.lower(), "Unknown")

    def get_related_skills(self, skill: str) -> list[str]:
        """
        Return sibling skills in the same category (excluding *skill* itself).
        """
        self._ensure_loaded()
        category = self.get_parent_skill(skill)
        if category == "Unknown":
            return []
        canonical = self.normalize_skill(skill)
        return [
            s
            for s in self._category_to_skills.get(category, [])
            if s.lower() != canonical.lower()
        ]

    def normalize_skill_list(self, skills: list[str]) -> list[str]:
        """
        Normalise every skill in *skills* and deduplicate while
        preserving order.
        """
        self._ensure_loaded()
        seen: set[str] = set()
        result: list[str] = []
        for skill in skills:
            normalised = self.normalize_skill(skill)
            key = normalised.lower()
            if key not in seen:
                seen.add(key)
                result.append(normalised)
        return result

# refactor: make _ensure_loaded format-agnostic to support both nested categories and flat category formats
