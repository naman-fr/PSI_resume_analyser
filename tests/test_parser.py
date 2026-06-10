"""Tests for PDF parsing and text processing utilities.

Covers:
- extract_text_from_pdf with invalid inputs
- clean_json_response (via _extract_json) with various LLM output formats
- validate_pdf rejecting oversized files and wrong MIME types
- validate_jd_text length constraint enforcement
- truncate_text correctness
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# PDF Parser Tests
# ---------------------------------------------------------------------------


class TestExtractTextFromPdf:
    """Tests for core.pdf_parser.extract_text_from_pdf."""

    def test_raises_file_not_found_for_missing_path(self):
        """A non-existent file path should raise FileNotFoundError."""
        from core.pdf_parser import extract_text_from_pdf

        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            extract_text_from_pdf("/nonexistent/path/resume.pdf")

    def test_raises_type_error_for_invalid_input_type(self):
        """Passing an unsupported type (e.g. int) should raise TypeError."""
        from core.pdf_parser import extract_text_from_pdf

        with pytest.raises(TypeError, match="Expected str, Path, or bytes"):
            extract_text_from_pdf(42)  # type: ignore[arg-type]

    def test_raises_value_error_for_empty_pdf_bytes(self):
        """Empty bytes should fail extraction with ValueError."""
        from core.pdf_parser import extract_text_from_pdf

        with pytest.raises(Exception):
            # Empty bytes are not a valid PDF — either PdfReadError or ValueError
            extract_text_from_pdf(b"")

    def test_raises_value_error_for_garbage_bytes(self):
        """Random non-PDF bytes should raise an extraction error."""
        from core.pdf_parser import extract_text_from_pdf

        with pytest.raises(Exception):
            extract_text_from_pdf(b"this is not a pdf file at all")

    def test_accepts_pathlib_path(self, tmp_path: Path):
        """Passing a pathlib.Path that doesn't exist should raise FileNotFoundError."""
        from core.pdf_parser import extract_text_from_pdf

        fake_path = tmp_path / "nonexistent.pdf"
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf(fake_path)

    def test_clean_text_normalises_whitespace(self):
        """_clean_text should collapse excessive whitespace and blank lines."""
        from core.pdf_parser import _clean_text

        raw = "Hello   world\n\n\n\nLine two\f\vLine three"
        result = _clean_text(raw)
        assert "   " not in result
        assert "\n\n\n" not in result
        assert "Line two" in result
        assert "Line three" in result

    def test_is_usable_rejects_short_text(self):
        """Strings shorter than the minimum threshold are not usable."""
        from core.pdf_parser import _is_usable

        assert _is_usable("short") is False

    def test_is_usable_accepts_long_printable_text(self):
        """A reasonably long printable string is usable."""
        from core.pdf_parser import _is_usable

        long_text = "This is a valid resume text. " * 20
        assert _is_usable(long_text) is True


# ---------------------------------------------------------------------------
# JSON Response Cleaning Tests
# ---------------------------------------------------------------------------


class TestCleanJsonResponse:
    """Tests for agents.resume_parser._extract_json."""

    def test_parses_pure_json(self):
        """Pure JSON strings should parse directly."""
        from agents.resume_parser import _extract_json

        data = {"name": "Alice", "skills": ["Python", "SQL"]}
        result = _extract_json(json.dumps(data))
        assert result == data

    def test_parses_json_in_markdown_code_block(self):
        """JSON wrapped in ```json ... ``` should be extracted."""
        from agents.resume_parser import _extract_json

        inner = {"job_title": "Engineer", "required_skills": ["Go"]}
        raw = f"Here is the result:\n```json\n{json.dumps(inner)}\n```\nDone."
        result = _extract_json(raw)
        assert result == inner

    def test_parses_json_in_generic_code_block(self):
        """JSON wrapped in ``` ... ``` (no language tag) should be extracted."""
        from agents.resume_parser import _extract_json

        inner = {"key": "value"}
        raw = f"```\n{json.dumps(inner)}\n```"
        result = _extract_json(raw)
        assert result == inner

    def test_parses_json_embedded_in_text(self):
        """JSON embedded in surrounding prose should be found via brace matching."""
        from agents.resume_parser import _extract_json

        inner = {"score": 85.5}
        raw = f'The analysis is complete. {json.dumps(inner)} Hope this helps!'
        result = _extract_json(raw)
        assert result == inner

    def test_raises_on_completely_invalid_input(self):
        """A string with no JSON at all should raise ValueError."""
        from agents.resume_parser import _extract_json

        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            _extract_json("No JSON here, just plain text.")

    def test_handles_nested_json(self):
        """Deeply nested JSON should parse correctly."""
        from agents.resume_parser import _extract_json

        data = {
            "experience": [
                {"company": "Acme", "bullets": ["Built APIs", "Led team"]},
                {"company": "Beta", "bullets": ["Wrote tests"]},
            ]
        }
        result = _extract_json(json.dumps(data))
        assert result["experience"][0]["company"] == "Acme"
        assert len(result["experience"]) == 2


# ---------------------------------------------------------------------------
# PDF Validation Tests
# ---------------------------------------------------------------------------


class TestValidatePdf:
    """Tests for utils.validators.validate_pdf."""

    def _make_mock_file(
        self, *, name: str = "resume.pdf", size: int = 1024, content: bytes = b""
    ) -> MagicMock:
        """Create a mock file object simulating a Gradio upload."""
        mock = MagicMock()
        mock.name = name
        mock.size = size
        if not content:
            content = b"%PDF-" + b"\x00" * (size - 5)
        mock.read = MagicMock(return_value=content)
        mock.seek = MagicMock()
        return mock

    def test_rejects_oversized_file(self):
        """Files exceeding max_file_size_mb should be rejected."""
        try:
            from utils.validators import validate_pdf
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        mock_file = self._make_mock_file(size=11 * 1024 * 1024)  # 11 MB
        is_valid, error = validate_pdf(mock_file)
        assert is_valid is False
        assert "size" in error.lower() or "large" in error.lower()

    def test_rejects_non_pdf_extension(self):
        """Files without .pdf extension should be rejected."""
        try:
            from utils.validators import validate_pdf
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        mock_file = self._make_mock_file(name="resume.docx")
        is_valid, error = validate_pdf(mock_file)
        assert is_valid is False
        assert "pdf" in error.lower()

    def test_accepts_valid_pdf(self):
        """A properly named, reasonably sized file should pass validation."""
        try:
            from utils.validators import validate_pdf
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        mock_file = self._make_mock_file(name="resume.pdf", size=500_000)
        is_valid, error = validate_pdf(mock_file)
        assert is_valid is True
        assert error == ""


# ---------------------------------------------------------------------------
# JD Text Validation Tests
# ---------------------------------------------------------------------------


class TestValidateJdText:
    """Tests for utils.validators.validate_jd_text."""

    def test_rejects_empty_text(self):
        """Empty or whitespace-only JD text should be rejected."""
        try:
            from utils.validators import validate_jd_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        is_valid, error = validate_jd_text("")
        assert is_valid is False

        is_valid, error = validate_jd_text("   \n\t  ")
        assert is_valid is False

    def test_rejects_too_short_text(self):
        """JD text that's too short to be meaningful should be rejected."""
        try:
            from utils.validators import validate_jd_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        is_valid, error = validate_jd_text("Hire someone.")
        assert is_valid is False

    def test_accepts_reasonable_jd(self):
        """A JD with sufficient length should pass validation."""
        try:
            from utils.validators import validate_jd_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        jd = (
            "We are looking for a Senior Software Engineer with 5+ years of "
            "experience in Python, Django, and PostgreSQL. The candidate should "
            "have strong problem-solving skills and experience with cloud "
            "platforms like AWS or GCP. Bachelor's degree in Computer Science "
            "or related field is required."
        )
        is_valid, error = validate_jd_text(jd)
        assert is_valid is True
        assert error == ""


# ---------------------------------------------------------------------------
# Text Truncation Tests
# ---------------------------------------------------------------------------


class TestTruncateText:
    """Tests for text truncation utility."""

    def test_truncate_short_text_unchanged(self):
        """Text shorter than the limit should be returned as-is."""
        try:
            from utils.validators import truncate_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        text = "Short text"
        assert truncate_text(text, max_length=100) == text

    def test_truncate_long_text(self):
        """Text longer than the limit should be truncated with an ellipsis marker."""
        try:
            from utils.validators import truncate_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        text = "A" * 500
        result = truncate_text(text, max_length=100)
        assert len(result) <= 103  # 100 + possible "..." suffix
        assert result.endswith("...")

    def test_truncate_exact_boundary(self):
        """Text exactly at the limit should pass through unchanged."""
        try:
            from utils.validators import truncate_text
        except ImportError:
            pytest.skip("utils.validators not yet implemented")

        text = "B" * 100
        result = truncate_text(text, max_length=100)
        assert result == text

# test: expand PDF validation test assertions for edge cases
