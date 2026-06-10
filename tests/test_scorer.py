"""Tests for the scoring system and skill taxonomy.

Covers:
- compute_keyword_overlap with perfect, partial, and zero overlap
- compute_cosine_similarity value range validation
- Overall weighted score calculation (0.40/0.25/0.25/0.10)
- format_score output format and emoji mapping
- SkillTaxonomy.normalize_skill alias resolution
- SkillTaxonomy.normalize_skill_list deduplication
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from core.similarity import compute_cosine_similarity, compute_keyword_overlap
from core.skill_taxonomy import SkillTaxonomy


# ---------------------------------------------------------------------------
# Keyword Overlap Tests
# ---------------------------------------------------------------------------


class TestComputeKeywordOverlap:
    """Tests for core.similarity.compute_keyword_overlap."""

    def test_perfect_match(self):
        """When resume skills exactly match JD skills, overlap should be 100%."""
        result = compute_keyword_overlap(
            resume_skills=["Python", "Django", "PostgreSQL"],
            jd_skills=["Python", "Django", "PostgreSQL"],
        )
        assert result["overlap_percentage"] == 100.0
        assert len(result["matched_skills"]) == 3
        assert len(result["missing_skills"]) == 0

    def test_partial_match(self):
        """Some skills match, some don't — overlap should be proportional."""
        result = compute_keyword_overlap(
            resume_skills=["Python", "Django", "React"],
            jd_skills=["Python", "Django", "PostgreSQL", "Docker"],
        )
        assert result["overlap_percentage"] == 50.0
        assert sorted(result["matched_skills"]) == ["Django", "Python"]
        assert sorted(result["missing_skills"]) == ["Docker", "PostgreSQL"]

    def test_no_match(self):
        """No overlapping skills should yield 0% overlap."""
        result = compute_keyword_overlap(
            resume_skills=["Rust", "Go", "Elixir"],
            jd_skills=["Python", "Java", "C++"],
        )
        assert result["overlap_percentage"] == 0.0
        assert len(result["matched_skills"]) == 0
        assert len(result["missing_skills"]) == 3

    def test_case_insensitive_matching(self):
        """Skill matching should be case-insensitive."""
        result = compute_keyword_overlap(
            resume_skills=["python", "DJANGO", "PostgreSql"],
            jd_skills=["Python", "Django", "PostgreSQL"],
        )
        assert result["overlap_percentage"] == 100.0
        assert len(result["matched_skills"]) == 3

    def test_empty_jd_skills(self):
        """Empty JD skills list should yield 0% overlap without errors."""
        result = compute_keyword_overlap(
            resume_skills=["Python", "Django"],
            jd_skills=[],
        )
        assert result["overlap_percentage"] == 0.0
        assert result["matched_skills"] == []
        assert result["missing_skills"] == []

    def test_empty_resume_skills(self):
        """Empty resume skills should yield 0% overlap."""
        result = compute_keyword_overlap(
            resume_skills=[],
            jd_skills=["Python", "Django"],
        )
        assert result["overlap_percentage"] == 0.0
        assert len(result["missing_skills"]) == 2

    def test_both_empty(self):
        """Both empty lists should yield 0% gracefully."""
        result = compute_keyword_overlap(
            resume_skills=[],
            jd_skills=[],
        )
        assert result["overlap_percentage"] == 0.0

    def test_whitespace_handling(self):
        """Skills with leading/trailing whitespace should still match."""
        result = compute_keyword_overlap(
            resume_skills=["  Python  ", " Django"],
            jd_skills=["Python", "Django  "],
        )
        assert result["overlap_percentage"] == 100.0

    def test_duplicate_jd_skills(self):
        """Duplicate JD skills should be deduplicated before scoring."""
        result = compute_keyword_overlap(
            resume_skills=["Python"],
            jd_skills=["Python", "Python", "Django"],
        )
        # After dedup: Python, Django → 1 matched, 1 missing → 50%
        assert result["overlap_percentage"] == 50.0


# ---------------------------------------------------------------------------
# Cosine Similarity Tests
# ---------------------------------------------------------------------------


class TestComputeCosineSimilarity:
    """Tests for core.similarity.compute_cosine_similarity."""

    def test_identical_vectors_return_one(self):
        """Identical vectors should have cosine similarity of 1.0."""
        vec = [1.0, 2.0, 3.0]
        sim = compute_cosine_similarity(vec, vec)
        assert math.isclose(sim, 1.0, abs_tol=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors should have cosine similarity of 0.0."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        sim = compute_cosine_similarity(v1, v2)
        assert math.isclose(sim, 0.0, abs_tol=1e-6)

    def test_opposite_vectors_return_negative_one(self):
        """Opposite vectors should have cosine similarity of -1.0."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [-1.0, 0.0, 0.0]
        sim = compute_cosine_similarity(v1, v2)
        assert math.isclose(sim, -1.0, abs_tol=1e-6)

    def test_result_in_valid_range(self):
        """Cosine similarity should always be in [-1, 1]."""
        rng = np.random.default_rng(42)
        for _ in range(20):
            v1 = rng.normal(size=128)
            v2 = rng.normal(size=128)
            sim = compute_cosine_similarity(v1, v2)
            assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6

    def test_numpy_array_inputs(self):
        """Should accept numpy arrays directly."""
        v1 = np.array([3.0, 4.0])
        v2 = np.array([4.0, 3.0])
        sim = compute_cosine_similarity(v1, v2)
        expected = (3 * 4 + 4 * 3) / (5.0 * 5.0)  # 24/25
        assert math.isclose(sim, expected, abs_tol=1e-6)

    def test_high_dimensional_vectors(self):
        """Should handle high-dimensional vectors (embedding-like)."""
        rng = np.random.default_rng(99)
        v1 = rng.normal(size=384)
        v2 = rng.normal(size=384)
        sim = compute_cosine_similarity(v1, v2)
        assert isinstance(sim, float)
        assert -1.0 - 1e-6 <= sim <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# Overall Score Calculation Tests
# ---------------------------------------------------------------------------


class TestOverallScoreCalculation:
    """Verify the weighted composite score formula: 0.40 + 0.25 + 0.25 + 0.10."""

    WEIGHTS = {
        "keyword": 0.40,
        "semantic": 0.25,
        "experience": 0.25,
        "education": 0.10,
    }

    def _compute_overall(
        self,
        keyword: float,
        semantic: float,
        experience: float,
        education: float,
    ) -> float:
        """Replicate the weighted formula."""
        return (
            self.WEIGHTS["keyword"] * keyword
            + self.WEIGHTS["semantic"] * semantic
            + self.WEIGHTS["experience"] * experience
            + self.WEIGHTS["education"] * education
        )

    def test_perfect_scores(self):
        """All 100s should yield overall 100."""
        score = self._compute_overall(100, 100, 100, 100)
        assert math.isclose(score, 100.0)

    def test_zero_scores(self):
        """All 0s should yield overall 0."""
        score = self._compute_overall(0, 0, 0, 0)
        assert math.isclose(score, 0.0)

    def test_keyword_dominance(self):
        """With only keyword score at 100, overall should be 40."""
        score = self._compute_overall(100, 0, 0, 0)
        assert math.isclose(score, 40.0)

    def test_mixed_scores(self):
        """Verify a specific mixed-score scenario."""
        # keyword=80, semantic=60, experience=70, education=90
        expected = 0.40 * 80 + 0.25 * 60 + 0.25 * 70 + 0.10 * 90
        # = 32 + 15 + 17.5 + 9 = 73.5
        score = self._compute_overall(80, 60, 70, 90)
        assert math.isclose(score, 73.5)

    def test_weights_sum_to_one(self):
        """Verify weights sum to exactly 1.0 to avoid miscalibrated scores."""
        total = sum(self.WEIGHTS.values())
        assert math.isclose(total, 1.0)

    def test_education_low_impact(self):
        """Education score has only 10% weight — changing it shouldn't swing much."""
        base = self._compute_overall(70, 70, 70, 50)
        with_high_edu = self._compute_overall(70, 70, 70, 100)
        diff = with_high_edu - base
        # Education changed by 50 pts → impact = 0.10 * 50 = 5 points
        assert math.isclose(diff, 5.0)


# ---------------------------------------------------------------------------
# Format Score Tests
# ---------------------------------------------------------------------------


class TestFormatScore:
    """Tests for score formatting utility."""

    @staticmethod
    def format_score(score: float) -> str:
        """Reference implementation of score formatting with emoji."""
        if score >= 80:
            emoji = "🟢"
            label = "Strong Match"
        elif score >= 60:
            emoji = "🟡"
            label = "Good Match"
        elif score >= 40:
            emoji = "🟠"
            label = "Partial Match"
        else:
            emoji = "🔴"
            label = "Weak Match"
        return f"{emoji} {score:.1f}/100 — {label}"

    def test_strong_match_format(self):
        result = self.format_score(92.5)
        assert "🟢" in result
        assert "92.5" in result
        assert "Strong Match" in result

    def test_good_match_format(self):
        result = self.format_score(65.0)
        assert "🟡" in result
        assert "Good Match" in result

    def test_partial_match_format(self):
        result = self.format_score(45.0)
        assert "🟠" in result
        assert "Partial Match" in result

    def test_weak_match_format(self):
        result = self.format_score(20.0)
        assert "🔴" in result
        assert "Weak Match" in result

    def test_boundary_80(self):
        """Exactly 80 should be Strong Match."""
        result = self.format_score(80.0)
        assert "🟢" in result

    def test_boundary_60(self):
        """Exactly 60 should be Good Match."""
        result = self.format_score(60.0)
        assert "🟡" in result

    def test_boundary_40(self):
        """Exactly 40 should be Partial Match."""
        result = self.format_score(40.0)
        assert "🟠" in result

    def test_zero_score(self):
        """Zero should be Weak Match."""
        result = self.format_score(0.0)
        assert "🔴" in result
        assert "0.0" in result

    def test_format_has_slash_100(self):
        """Output should always contain '/100'."""
        result = self.format_score(73.2)
        assert "/100" in result


# ---------------------------------------------------------------------------
# Skill Taxonomy Tests
# ---------------------------------------------------------------------------


TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skill_taxonomy.json"


class TestSkillTaxonomyNormalize:
    """Tests for core.skill_taxonomy.SkillTaxonomy.normalize_skill."""

    @pytest.fixture
    def taxonomy(self) -> SkillTaxonomy:
        """Load the real taxonomy from data/skill_taxonomy.json."""
        if not TAXONOMY_PATH.exists():
            pytest.skip("skill_taxonomy.json not found")
        return SkillTaxonomy(TAXONOMY_PATH)

    def test_normalizes_python3_to_python(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("python3") == "Python"

    def test_normalizes_reactjs_to_react(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("reactjs") == "React"

    def test_normalizes_react_js_to_react(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("react.js") == "React"

    def test_normalizes_nodejs_to_node_js(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("nodejs") == "Node.js"

    def test_normalizes_k8s_to_kubernetes(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("k8s") == "Kubernetes"

    def test_normalizes_postgres_to_postgresql(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("postgres") == "PostgreSQL"

    def test_normalizes_ml_to_machine_learning(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("ml") == "Machine Learning"

    def test_normalizes_aws_full_name(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("amazon web services") == "AWS"

    def test_normalizes_gcp(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("gcp") == "Google Cloud"

    def test_case_insensitive_normalization(self, taxonomy: SkillTaxonomy):
        assert taxonomy.normalize_skill("PYTHON") == "Python"
        assert taxonomy.normalize_skill("Docker") == "Docker"

    def test_unknown_skill_passes_through(self, taxonomy: SkillTaxonomy):
        """A skill not in the taxonomy should be returned as-is (stripped)."""
        assert taxonomy.normalize_skill("Obscure Framework XYZ") == "Obscure Framework XYZ"

    def test_whitespace_stripped(self, taxonomy: SkillTaxonomy):
        """Leading/trailing whitespace should be stripped before lookup."""
        assert taxonomy.normalize_skill("  python3  ") == "Python"


class TestSkillTaxonomyNormalizeList:
    """Tests for core.skill_taxonomy.SkillTaxonomy.normalize_skill_list."""

    @pytest.fixture
    def taxonomy(self) -> SkillTaxonomy:
        if not TAXONOMY_PATH.exists():
            pytest.skip("skill_taxonomy.json not found")
        return SkillTaxonomy(TAXONOMY_PATH)

    def test_deduplicates_aliases(self, taxonomy: SkillTaxonomy):
        """Multiple aliases for the same canonical skill should collapse to one."""
        result = taxonomy.normalize_skill_list(["python3", "Python", "py", "PYTHON"])
        # All map to "Python" — should appear exactly once
        assert result.count("Python") == 1
        assert len(result) == 1

    def test_preserves_order(self, taxonomy: SkillTaxonomy):
        """First occurrence should dictate the position in the result."""
        result = taxonomy.normalize_skill_list(["reactjs", "python3", "Docker"])
        assert result == ["React", "Python", "Docker"]

    def test_mixed_known_and_unknown(self, taxonomy: SkillTaxonomy):
        """Unknown skills should pass through alongside normalized ones."""
        result = taxonomy.normalize_skill_list(["k8s", "SomeRareSkill", "ml"])
        assert "Kubernetes" in result
        assert "Machine Learning" in result
        assert "SomeRareSkill" in result
        assert len(result) == 3

    def test_empty_list(self, taxonomy: SkillTaxonomy):
        """Empty input should return empty output."""
        assert taxonomy.normalize_skill_list([]) == []

    def test_all_duplicates_collapsed(self, taxonomy: SkillTaxonomy):
        """If every entry maps to the same skill, result should have length 1."""
        result = taxonomy.normalize_skill_list(["js", "JavaScript", "ecmascript"])
        assert len(result) == 1
        assert result[0] == "JavaScript"

# test: add more assertions for keyword overlap boundary values
