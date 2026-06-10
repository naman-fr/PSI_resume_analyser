"""
PDF text extraction module.

Uses PyPDF2 as the primary extractor and falls back to pdfplumber when
PyPDF2 returns empty or low-quality text.  Accepts either a filesystem
path (str / pathlib.Path) or raw PDF bytes (for Gradio uploads).
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Union

import pdfplumber
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MIN_USEFUL_LENGTH = 50  # characters – below this we assume extraction failed


def _clean_text(raw: str) -> str:
    """Normalise whitespace and strip control characters from extracted text."""
    # Replace form-feeds and vertical tabs with newlines
    text = re.sub(r"[\f\v]", "\n", raw)
    # Collapse runs of blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse horizontal whitespace (but not newlines) into a single space
    text = re.sub(r"[^\S\n]+", " ", text)
    # Strip leading/trailing whitespace on every line
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def _is_usable(text: str) -> bool:
    """Heuristic: does the extracted text look like real content?"""
    if len(text) < _MIN_USEFUL_LENGTH:
        return False
    # If more than 30 % of characters are non-ASCII-printable, probably garbage
    printable_ratio = sum(c.isprintable() or c in "\n\t" for c in text) / max(len(text), 1)
    return printable_ratio > 0.70


def _open_as_stream(file_path_or_bytes: Union[str, Path, bytes]) -> io.BytesIO:
    """Return a seekable BytesIO stream regardless of input type."""
    if isinstance(file_path_or_bytes, (str, Path)):
        path = Path(file_path_or_bytes)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        return io.BytesIO(path.read_bytes())
    if isinstance(file_path_or_bytes, bytes):
        return io.BytesIO(file_path_or_bytes)
    raise TypeError(
        f"Expected str, Path, or bytes, got {type(file_path_or_bytes).__name__}"
    )


# ---------------------------------------------------------------------------
# Extraction back-ends
# ---------------------------------------------------------------------------


def _extract_with_pypdf2(stream: io.BytesIO) -> str:
    """Extract text using PyPDF2."""
    stream.seek(0)
    reader = PdfReader(stream)
    pages: list[str] = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        logger.debug("PyPDF2 page %d: %d chars", page_num, len(page_text))
        pages.append(page_text)
    return "\n".join(pages)


def _extract_with_pdfplumber(stream: io.BytesIO) -> str:
    """Extract text using pdfplumber (fallback)."""
    stream.seek(0)
    pages: list[str] = []
    with pdfplumber.open(stream) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            logger.debug("pdfplumber page %d: %d chars", page_num, len(page_text))
            pages.append(page_text)
    return "\n".join(pages)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_text_from_pdf(file_path_or_bytes: Union[str, Path, bytes]) -> str:
    """
    Extract and clean text from a PDF document.

    Parameters
    ----------
    file_path_or_bytes:
        Either a filesystem path to a PDF file **or** raw PDF bytes
        (useful for in-memory uploads from Gradio).

    Returns
    -------
    str
        Cleaned, human-readable text extracted from all pages.

    Raises
    ------
    FileNotFoundError
        If a path is provided and the file does not exist.
    ValueError
        If no usable text could be extracted by any back-end.
    """
    stream = _open_as_stream(file_path_or_bytes)

    # --- Primary: PyPDF2 ---
    try:
        text = _extract_with_pypdf2(stream)
        text = _clean_text(text)
        if _is_usable(text):
            logger.info("Extracted %d chars with PyPDF2", len(text))
            return text
        logger.warning("PyPDF2 returned low-quality text; falling back to pdfplumber")
    except (PdfReadError, Exception) as exc:
        logger.warning("PyPDF2 failed (%s); falling back to pdfplumber", exc)

    # --- Fallback: pdfplumber ---
    try:
        text = _extract_with_pdfplumber(stream)
        text = _clean_text(text)
        if _is_usable(text):
            logger.info("Extracted %d chars with pdfplumber", len(text))
            return text
        logger.error("pdfplumber also returned low-quality text")
    except Exception as exc:
        logger.error("pdfplumber also failed: %s", exc)

    raise ValueError(
        "Could not extract usable text from the PDF with any available back-end."
    )

# refactor: add more logging details for PDF parsing fallbacks
