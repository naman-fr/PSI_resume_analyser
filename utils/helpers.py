"""Helper utility functions for PSI Resume Analyser."""

import json
import re
from typing import Any


def format_score(score: float) -> str:
    """Format a numerical score as a colored string with emoji indicator.

    Args:
        score: A float between 0 and 100 representing the score.

    Returns:
        A formatted string like "🟢 85.2/100" with color emoji based on thresholds:
        - Green (🟢) for scores >= 70
        - Yellow (🟡) for scores >= 50
        - Red (🔴) for scores < 50
    """
    if score is None:
        return "⚪ N/A"
    try:
        score_val = float(score)
    except (TypeError, ValueError):
        return "⚪ N/A"
    if score_val >= 70:
        emoji = "🟢"
    elif score_val >= 50:
        emoji = "🟡"
    else:
        emoji = "🔴"
    return f"{emoji} {score_val:.1f}/100"


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length, appending an ellipsis if truncated.

    Args:
        text: The input text to truncate.
        max_length: Maximum allowed character length (default 500).

    Returns:
        The original text if within limits, otherwise the truncated text
        with '...' appended.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def clean_json_response(response: str) -> dict:
    """Extract and parse JSON from an LLM response string.

    LLM responses often wrap JSON inside markdown code fences like
    ```json ... ```. This function handles that by first attempting a
    direct ``json.loads``, then falling back to regex extraction of
    fenced JSON blocks, and finally trying to find any top-level JSON
    object in the raw text.

    Args:
        response: The raw string response from an LLM.

    Returns:
        A parsed dictionary on success, or an empty dict on failure.
    """
    if not response or not response.strip():
        return {}

    text = response.strip()

    # Attempt 1: direct parse — works when the LLM returns clean JSON.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Attempt 2: extract from markdown ```json ... ``` code fences.
    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    match = fence_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # Attempt 3: find the first top-level JSON object in the string.
    brace_pattern = re.compile(r"\{.*\}", re.DOTALL)
    match = brace_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    return {}


def format_time_elapsed(seconds: float) -> str:
    """Format elapsed seconds into a human-readable duration string.

    Args:
        seconds: The number of seconds elapsed.

    Returns:
        A string like "2.3s" for short durations or "1m 5s" for longer ones.
    """
    if seconds < 0:
        seconds = 0.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"


def create_score_bar(score: float, max_width: int = 20) -> str:
    """Create a text-based progress bar representing a score percentage.

    Args:
        score: A float between 0 and 100.
        max_width: The total number of bar characters (default 20).

    Returns:
        A string like ``[████████░░░░░░░░░░░░] 40%``.
    """
    if score is None:
        score = 0.0
    try:
        score_val = float(score)
    except (TypeError, ValueError):
        score_val = 0.0
    clamped = max(0.0, min(100.0, score_val))
    filled = int(round(clamped / 100 * max_width))
    empty = max_width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {int(round(clamped))}%"


def safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely retrieve a value from a nested dictionary.

    Args:
        d: The root dictionary.
        *keys: A sequence of keys representing the path into nested dicts.
        default: The value to return if any key is missing (default ``None``).

    Returns:
        The value at the nested key path, or *default* if not found.

    Example::

        data = {"a": {"b": {"c": 42}}}
        safe_get(data, "a", "b", "c")          # 42
        safe_get(data, "a", "x", default=0)    # 0
    """
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current

# refactor: optimize progress score bar formatting output
