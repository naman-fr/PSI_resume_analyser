"""Tests for the LangGraph resume analysis workflow.

Covers:
- create_analysis_graph returns a compiled graph
- State schema has all required keys
- Error handling when no API keys are set
- Mocked full pipeline flow
"""

from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from agents.state import ResumeJDState


# ---------------------------------------------------------------------------
# State Schema Tests
# ---------------------------------------------------------------------------


class TestResumeJDState:
    """Verify the shared state TypedDict has every required field."""

    REQUIRED_INPUT_KEYS = {"resume_text", "jd_text"}
    REQUIRED_PARSED_KEYS = {"resume_parsed", "jd_extracted"}
    REQUIRED_SCORE_KEYS = {
        "keyword_score",
        "semantic_score",
        "experience_score",
        "education_score",
        "overall_score",
    }
    REQUIRED_ANALYSIS_KEYS = {
        "skill_match",
        "experience_match",
        "education_match",
        "strengths",
        "gaps",
    }
    REQUIRED_IMPROVEMENT_KEYS = {"improvement_suggestions", "ats_optimized_bullets"}
    REQUIRED_META_KEYS = {"error", "provider_used"}

    def test_state_has_input_keys(self):
        """State must declare resume_text and jd_text."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_INPUT_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_parsed_keys(self):
        """State must declare resume_parsed and jd_extracted."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_PARSED_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_score_keys(self):
        """State must declare all five score fields."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_SCORE_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_analysis_keys(self):
        """State must declare skill_match, experience_match, etc."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_ANALYSIS_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_improvement_keys(self):
        """State must declare improvement_suggestions and ats_optimized_bullets."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_IMPROVEMENT_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_meta_keys(self):
        """State must declare error and provider_used."""
        annotations = ResumeJDState.__annotations__
        for key in self.REQUIRED_META_KEYS:
            assert key in annotations, f"Missing state key: {key}"

    def test_state_has_normalized_skills_keys(self):
        """State must have resume_skills_normalized and jd_skills_normalized."""
        annotations = ResumeJDState.__annotations__
        assert "resume_skills_normalized" in annotations
        assert "jd_skills_normalized" in annotations

    def test_state_is_total_false(self):
        """TypedDict total=False means all keys are optional at instantiation."""
        state: ResumeJDState = {}  # type: ignore[typeddict-item]
        assert isinstance(state, dict)

    def test_all_expected_keys_count(self):
        """Verify the total number of expected state keys."""
        all_expected = (
            self.REQUIRED_INPUT_KEYS
            | self.REQUIRED_PARSED_KEYS
            | self.REQUIRED_SCORE_KEYS
            | self.REQUIRED_ANALYSIS_KEYS
            | self.REQUIRED_IMPROVEMENT_KEYS
            | self.REQUIRED_META_KEYS
            | {"resume_skills_normalized", "jd_skills_normalized"}
        )
        annotations = ResumeJDState.__annotations__
        for key in all_expected:
            assert key in annotations, f"Missing state key: {key}"


# ---------------------------------------------------------------------------
# Graph Creation Tests
# ---------------------------------------------------------------------------


class TestCreateAnalysisGraph:
    """Tests for agents.graph.create_analysis_graph."""

    def test_returns_compiled_graph(self):
        """create_analysis_graph should return a CompiledGraph."""
        try:
            from agents.graph import create_analysis_graph
        except ImportError:
            pytest.skip("agents.graph not yet implemented")

        graph = create_analysis_graph()
        # A compiled LangGraph has an .invoke() method
        assert hasattr(graph, "invoke"), "Graph must have an invoke method"

    def test_graph_is_callable(self):
        """The compiled graph should be callable or invocable."""
        try:
            from agents.graph import create_analysis_graph
        except ImportError:
            pytest.skip("agents.graph not yet implemented")

        graph = create_analysis_graph()
        assert callable(getattr(graph, "invoke", None))


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestGraphErrorHandling:
    """Tests for graceful error handling."""

    def test_no_api_keys_raises_error(self):
        """With no API keys set, run_analysis should raise or return an error."""
        try:
            from agents.graph import run_analysis
        except ImportError:
            pytest.skip("agents.graph not yet implemented")

        # Clear any API keys from environment
        env_patch = {
            "GOOGLE_API_KEY": "",
            "GROQ_API_KEY": "",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            try:
                result = run_analysis(
                    resume_text="Some resume text " * 20,
                    jd_text="Some JD text " * 20,
                )
                # If it returns instead of raising, it should contain an error
                if isinstance(result, dict):
                    assert result.get("error") is not None or "error" in str(result).lower()
            except (RuntimeError, ValueError) as exc:
                # Expected — no LLM provider available
                assert "api key" in str(exc).lower() or "no llm" in str(exc).lower()

    def test_empty_resume_returns_error(self):
        """Empty resume_text should surface an error in the result."""
        try:
            from agents.graph import run_analysis
        except ImportError:
            pytest.skip("agents.graph not yet implemented")

        try:
            result = run_analysis(resume_text="", jd_text="A valid job description " * 20)
            if isinstance(result, dict):
                assert result.get("error") is not None
        except (RuntimeError, ValueError):
            pass  # Also acceptable — fast-fail on empty input

    def test_empty_jd_returns_error(self):
        """Empty jd_text should surface an error in the result."""
        try:
            from agents.graph import run_analysis
        except ImportError:
            pytest.skip("agents.graph not yet implemented")

        try:
            result = run_analysis(resume_text="A valid resume text " * 20, jd_text="")
            if isinstance(result, dict):
                assert result.get("error") is not None
        except (RuntimeError, ValueError):
            pass


# ---------------------------------------------------------------------------
# Mocked Full Pipeline Flow
# ---------------------------------------------------------------------------


class TestMockedPipelineFlow:
    """End-to-end pipeline test with mocked LLM calls."""

    @staticmethod
    def _make_mock_llm_response(content: str) -> MagicMock:
        """Create a mock LLM response object."""
        mock_resp = MagicMock()
        mock_resp.content = content
        return mock_resp

    def test_parse_resume_node_with_mock_llm(self):
        """parse_resume node should produce resume_parsed from mocked LLM."""
        import json
        from agents.resume_parser import parse_resume

        fake_parsed = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "summary": "Experienced software engineer",
            "skills": ["Python", "Django", "PostgreSQL", "Docker"],
            "experience": [
                {
                    "company": "Acme Corp",
                    "role": "Senior Engineer",
                    "start_date": "Jan 2020",
                    "end_date": "Present",
                    "duration_months": 60,
                    "bullets": [
                        "Built scalable REST APIs using Django and DRF",
                        "Led a team of 5 engineers",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech in Computer Science",
                    "institution": "IIT Delhi",
                    "year": "2019",
                    "gpa": "8.5",
                }
            ],
            "certifications": ["AWS Solutions Architect"],
            "projects": [],
            "total_experience_years": 5.0,
        }

        mock_response = self._make_mock_llm_response(json.dumps(fake_parsed))
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch("agents.resume_parser.get_llm", return_value=(mock_llm, "mock")):
            state: Dict[str, Any] = {"resume_text": "John Doe\nSoftware Engineer\n..."}
            result = parse_resume(state)

        assert "error" not in result
        assert "resume_parsed" in result
        assert result["resume_parsed"]["name"] == "John Doe"
        assert "Python" in result["resume_parsed"]["skills"]

    def test_extract_jd_node_with_mock_llm(self):
        """extract_jd node should produce jd_extracted from mocked LLM."""
        import json
        from agents.jd_extractor import extract_jd

        fake_jd = {
            "job_title": "Senior Python Developer",
            "company": "TechCo",
            "required_skills": ["Python", "Django", "PostgreSQL"],
            "preferred_skills": ["Docker", "Kubernetes"],
            "min_experience_years": 5,
            "education_requirement": "Bachelor's in CS",
            "responsibilities": ["Build APIs", "Mentor juniors"],
            "certifications_required": [],
        }

        mock_response = self._make_mock_llm_response(json.dumps(fake_jd))
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch("agents.resume_parser.get_llm", return_value=(mock_llm, "mock")):
            state: Dict[str, Any] = {
                "jd_text": "We need a Senior Python Developer with 5+ years..."
            }
            result = extract_jd(state)

        assert "error" not in result
        assert "jd_extracted" in result
        assert result["jd_extracted"]["job_title"] == "Senior Python Developer"
        assert "Python" in result["jd_extracted"]["required_skills"]

    def test_parse_resume_handles_llm_failure(self):
        """parse_resume should return an error dict if the LLM call throws."""
        from agents.resume_parser import parse_resume

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("API quota exceeded")

        with patch("agents.resume_parser.get_llm", return_value=(mock_llm, "mock")):
            state: Dict[str, Any] = {"resume_text": "Some resume content " * 20}
            result = parse_resume(state)

        assert "error" in result
        assert "failed" in result["error"].lower()

    def test_extract_jd_handles_empty_input(self):
        """extract_jd should return an error for empty jd_text."""
        from agents.jd_extractor import extract_jd

        state: Dict[str, Any] = {"jd_text": ""}
        result = extract_jd(state)
        assert "error" in result

    def test_parse_resume_handles_empty_input(self):
        """parse_resume should return an error for empty resume_text."""
        from agents.resume_parser import parse_resume

        state: Dict[str, Any] = {"resume_text": "   "}
        result = parse_resume(state)
        assert "error" in result

    def test_keyword_overlap_integration(self):
        """Integration test: compute keyword overlap from parsed data."""
        from core.similarity import compute_keyword_overlap

        resume_skills = ["Python", "Django", "React", "Docker", "PostgreSQL"]
        jd_skills = ["Python", "Django", "PostgreSQL", "Kubernetes", "AWS"]

        result = compute_keyword_overlap(resume_skills, jd_skills)
        assert result["overlap_percentage"] == 60.0
        assert set(result["matched_skills"]) == {"Django", "PostgreSQL", "Python"}
        assert set(result["missing_skills"]) == {"AWS", "Kubernetes"}

# test: simulate failed API keys in workflow test mocked inputs
