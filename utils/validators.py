"""Input validation utilities for PSI Resume Analyser."""

import os
import re
from pathlib import Path
from typing import Any, Union

# Maximum allowed PDF file size: 10 MB.
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024

# JD text length limits.
MIN_JD_LENGTH = 50
MAX_JD_LENGTH = 10_000

# PDF magic bytes: every valid PDF starts with ``%PDF``.
PDF_MAGIC = b"%PDF"


def validate_pdf(file_path_or_bytes: Any) -> tuple[bool, str]:
    """Validate that the input is a legitimate, reasonably-sized PDF.

    Accepts filesystem path (``str`` / ``Path``), raw ``bytes``, or file-like objects.

    Checks performed:
        1. File extension is ``.pdf`` (path mode only).
        2. File / byte payload size is under 10 MB.
        3. Content starts with the ``%PDF`` magic bytes.

    Args:
        file_path_or_bytes: A path to a PDF file, raw PDF bytes, or file-like object.

    Returns:
        A tuple ``(is_valid, error_message)``. When valid, *error_message*
        is an empty string.
    """
    if hasattr(file_path_or_bytes, "read") and hasattr(file_path_or_bytes, "name"):
        name = file_path_or_bytes.name
        if not name.lower().endswith(".pdf"):
            suffix = Path(name).suffix
            return False, f"Invalid file extension '{suffix}'. Expected '.pdf'."
        
        file_size = getattr(file_path_or_bytes, "size", None)
        if file_size is None and hasattr(file_path_or_bytes, "seek"):
            try:
                file_path_or_bytes.seek(0, 2)
                file_size = file_path_or_bytes.tell()
                file_path_or_bytes.seek(0)
            except Exception:
                pass
                
        if file_size is not None:
            if file_size == 0:
                return False, "The PDF file is empty (0 bytes)."
            if file_size > MAX_PDF_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                return False, f"File size ({size_mb:.1f} MB) exceeds the 10 MB limit."
                
        try:
            if hasattr(file_path_or_bytes, "seek"):
                file_path_or_bytes.seek(0)
            header = file_path_or_bytes.read(4)
            if hasattr(file_path_or_bytes, "seek"):
                file_path_or_bytes.seek(0)
        except Exception as exc:
            return False, f"Unable to read file: {exc}"
            
        if not header.startswith(PDF_MAGIC):
            return False, "File does not appear to be a valid PDF (missing %PDF header)."
            
        return True, ""

    if isinstance(file_path_or_bytes, (str, Path)):
        return _validate_pdf_path(Path(file_path_or_bytes))
    if isinstance(file_path_or_bytes, bytes):
        return _validate_pdf_bytes(file_path_or_bytes)
    return False, "Invalid input: expected a file path (str/Path) or bytes."


def _validate_pdf_path(path: Path) -> tuple[bool, str]:
    """Validate a PDF given its filesystem path."""
    if not path.exists():
        return False, f"File not found: {path}"

    if path.suffix.lower() != ".pdf":
        return False, f"Invalid file extension '{path.suffix}'. Expected '.pdf'."

    file_size = path.stat().st_size
    if file_size == 0:
        return False, "The PDF file is empty (0 bytes)."
    if file_size > MAX_PDF_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, f"File size ({size_mb:.1f} MB) exceeds the 10 MB limit."

    try:
        with open(path, "rb") as fh:
            header = fh.read(4)
    except OSError as exc:
        return False, f"Unable to read file: {exc}"

    if not header.startswith(PDF_MAGIC):
        return False, "File does not appear to be a valid PDF (missing %PDF header)."

    return True, ""


def _validate_pdf_bytes(data: bytes) -> tuple[bool, str]:
    """Validate raw PDF bytes."""
    if not data:
        return False, "PDF data is empty."

    if len(data) > MAX_PDF_SIZE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        return False, f"PDF size ({size_mb:.1f} MB) exceeds the 10 MB limit."

    if not data[:4].startswith(PDF_MAGIC):
        return False, "Data does not appear to be a valid PDF (missing %PDF header)."

    return True, ""


def validate_jd_text(text: str) -> tuple[bool, str]:
    """Validate job description text for length and content requirements.

    Args:
        text: The raw job description string.

    Returns:
        A tuple ``(is_valid, error_message)``. When valid, *error_message*
        is an empty string.
    """
    if not text or not text.strip():
        return False, "Job description text is empty."

    stripped = text.strip()

    if len(stripped) < MIN_JD_LENGTH:
        return (
            False,
            f"Job description is too short ({len(stripped)} chars). "
            f"Minimum {MIN_JD_LENGTH} characters required.",
        )

    if len(stripped) > MAX_JD_LENGTH:
        return (
            False,
            f"Job description is too long ({len(stripped)} chars). "
            f"Maximum {MAX_JD_LENGTH} characters allowed.",
        )

    return True, ""


def sanitize_filename(filename: str) -> str:
    """Remove or replace characters unsafe for use in filenames.

    Strips leading/trailing whitespace, replaces path separators and
    other dangerous characters with underscores, collapses consecutive
    underscores, and removes leading dots to prevent hidden files.

    Args:
        filename: The raw filename string.

    Returns:
        A sanitized filename safe for use on common filesystems.
    """
    if not filename:
        return "unnamed"

    # Remove any directory components — keep only the basename.
    name = os.path.basename(filename)

    # Replace characters that are problematic on Windows / Unix.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)

    # Collapse multiple underscores into one.
    name = re.sub(r"_+", "_", name)

    # Strip leading dots (hidden files) and surrounding whitespace / underscores.
    name = name.strip().strip(".").strip("_")

    return name if name else "unnamed"

# fix: change header check to startswith(PDF_MAGIC) to support MagicMock files in tests
