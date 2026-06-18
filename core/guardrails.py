"""Safety and Security Guardrails for PSI Resume Analyser."""

import logging
import re
import json
import urllib.request
import urllib.parse
from typing import Dict, Tuple, Any
import pdfplumber
from config.settings import settings

logger = logging.getLogger(__name__)


def scan_prompt_injection(text: str) -> Tuple[bool, float, str]:
    """Scan input text for adversarial prompt injection attempts.

    Parameters
    ----------
    text : str
        The raw resume or job description text.

    Returns
    -------
    (is_injection, confidence, reason)
        A tuple containing the scanning results.
    """
    if not text:
        return False, 0.0, ""

    # Adversarial instruction patterns
    injection_patterns = [
        (r"(?i)ignore\s+(?:all\s+)?previous\s+instructions", 0.95, "Ignore instructions override attempt"),
        (r"(?i)system\s+override|system\s+prompt\s+bypass", 0.90, "System prompt bypass attempt"),
        (r"(?i)you\s+must\s+award\s+(?:a\s+)?score\s+of\s+100", 0.99, "Score manipulation instruction"),
        (r"(?i)forget\s+everything\s+written\s+above", 0.85, "Context clearing instruction"),
        (r"(?i)new\s+role\s+definition|you\s+are\s+now\s+an\s+assistant", 0.80, "Role hijacking instruction"),
        (r"(?i)override\s+ats\s+scoring\s+rules", 0.95, "Scoring override instruction"),
        (r"(?i)output\s+only\s+the\s+following\s+json", 0.70, "Formatting hijack attempt")
    ]

    max_confidence = 0.0
    triggered_reason = ""

    for pattern, confidence, reason in injection_patterns:
        if re.search(pattern, text):
            if confidence > max_confidence:
                max_confidence = confidence
                triggered_reason = reason

    is_injection = max_confidence >= 0.75
    if is_injection:
        logger.warning(
            "Prompt injection detected! Pattern: '%s', Confidence: %.2f",
            triggered_reason,
            max_confidence
        )

    return is_injection, max_confidence, triggered_reason


def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """Scrub personal identifiable information (PII) to reduce demographic bias.

    Masks emails, phone numbers, and social media/portfolio links.

    Parameters
    ----------
    text : str
        The raw resume text.

    Returns
    -------
    (masked_text, redacting_map)
        The masked string and a dictionary of the original to redacted mappings.
    """
    if not text:
        return "", {}

    redacting_map: Dict[str, str] = {}
    masked_text = text

    # 1. Mask Emails
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    emails = re.findall(email_pattern, masked_text)
    for idx, email in enumerate(emails):
        placeholder = f"[EMAIL_REDACTED_{idx+1}]"
        redacting_map[placeholder] = email
        masked_text = masked_text.replace(email, placeholder)

    # 2. Mask Phone Numbers
    phone_patterns = [
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", # 10-digit
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{4}\b"               # 7-digit
    ]
    raw_phones = []
    for pattern in phone_patterns:
        raw_phones.extend(re.findall(pattern, masked_text))
    phones = list(dict.fromkeys(raw_phones))
    for idx, phone in enumerate(phones):
        # Prevent masking simple years or short numbers
        if len(re.sub(r"\D", "", phone)) >= 7:
            placeholder = f"[PHONE_REDACTED_{idx+1}]"
            redacting_map[placeholder] = phone
            masked_text = masked_text.replace(phone, placeholder)

    # 3. Mask Social Links / Portfolios (LinkedIn, GitHub)
    link_pattern = r"(?:https?://)?(?:www\.)?(?:linkedin\.com/in|github\.com)/[A-Za-z0-9_-]+"
    links = re.findall(link_pattern, masked_text)
    for idx, link in enumerate(links):
        placeholder = f"[LINK_REDACTED_{idx+1}]"
        redacting_map[placeholder] = link
        masked_text = masked_text.replace(link, placeholder)

    # 4. Optional: Mask common candidate headers (Name: ...)
    name_header_pattern = r"(?i)(?:name|candidate)\s*:\s*([A-Za-z\s]+)\b"
    name_matches = re.finditer(name_header_pattern, masked_text)
    for idx, match in enumerate(name_matches):
        original_name = match.group(1).strip()
        if len(original_name.split()) <= 4:  # Avoid matching entire blocks
            placeholder = f"[NAME_REDACTED_{idx+1}]"
            redacting_map[placeholder] = original_name
            masked_text = masked_text.replace(original_name, placeholder)

    return masked_text, redacting_map


def _is_char_white(char: dict) -> bool:
    """Helper to check if a character has a white/near-white color representation."""
    color = char.get("non_stroking_color")
    if color is None:
        return False
        
    if isinstance(color, (list, tuple)):
        if len(color) == 3:  # RGB
            return all(c >= 0.95 for c in color)
        elif len(color) == 4:  # CMYK (0,0,0,0 is white)
            return all(c <= 0.05 for c in color)
        elif len(color) == 1:  # Grayscale
            return color[0] >= 0.95
    elif isinstance(color, (int, float)):  # Grayscale / float
        return color >= 0.95
    return False


def detect_invisible_text(pdf_file) -> Tuple[bool, list, float]:
    """Scan a PDF file using pdfplumber to detect white/near-white hidden text.

    Parameters
    ----------
    pdf_file : file-like object or str
        The path to the PDF or a file-like stream object.

    Returns
    -------
    (is_flagged, detected_words, penalty)
        A tuple containing boolean flag, list of detected words/keywords, and scoring penalty.
    """
    detected_words = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                chars = page.chars
                current_white_word = []
                for char in chars:
                    char_text = char.get("text", "")
                    if _is_char_white(char):
                        if char_text.strip() and char_text.isalnum():
                            current_white_word.append(char_text)
                        else:
                            if current_white_word:
                                word = "".join(current_white_word)
                                if len(word) > 2:
                                    detected_words.append(word)
                                current_white_word = []
                    else:
                        if current_white_word:
                            word = "".join(current_white_word)
                            if len(word) > 2:
                                detected_words.append(word)
                            current_white_word = []
                            
                # Check end of page
                if current_white_word:
                    word = "".join(current_white_word)
                    if len(word) > 2:
                        detected_words.append(word)
    except Exception as e:
        logger.warning("Failed to scan PDF for invisible text: %s", e)

    detected_words = list(set(detected_words))
    is_flagged = len(detected_words) > 0
    penalty = -25.0 if is_flagged else 0.0
    return is_flagged, detected_words, penalty


def _ping_url(url: str, timeout: float = 5.0) -> Tuple[bool, int, str]:
    """Ping a URL and return if it is valid, the status code, and a log message."""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)

    hostname = parsed.hostname or ""
    if hostname.lower() in ["localhost", "127.0.0.1"]:
        return False, 400, f"Invalid domain: {hostname}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PSI-Resume-Analyser/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            return True, status, f"Link reachable (HTTP {status})"
    except urllib.error.HTTPError as e:
        status = e.code
        # Treat 403 and 999 as active but blocked (so valid candidate link)
        if status in [403, 999]:
            return True, status, f"Link active but crawler blocked (HTTP {status})"
        elif status == 404:
            return False, status, "Profile not found (HTTP 404)"
        else:
            return False, status, f"Reachable but returned HTTP {status}"
    except Exception as e:
        return False, 500, f"Connection failed: {str(e)}"


def _get_github_repo_count(url: str) -> int:
    """Attempts to fetch public repo count for a GitHub profile using GitHub's public API."""
    path = urllib.parse.urlparse(url).path
    parts = [p for p in path.split("/") if p]
    if not parts:
        return 0
    username = parts[0]

    # Exclude common non-user routes
    if username.lower() in ["about", "pricing", "features", "explore", "trending", "settings", "marketplace", "contact"]:
        return 0

    api_url = f"https://api.github.com/users/{username}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "PSI-Resume-Analyser/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("public_repos", 0)
    except Exception as e:
        logger.debug("GitHub API fetch failed for %s: %s", username, e)
        # HTML Scrape fallback
        try:
            req = urllib.request.Request(
                f"https://github.com/{username}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PSI-Resume-Analyser/1.0"}
            )
            with urllib.request.urlopen(req, timeout=4.0) as response:
                html = response.read().decode("utf-8")
                match = re.search(r'Repositories\s*<span[^>]*class="Counter"[^>]*>(\d+)</span>', html)
                if match:
                    return int(match.group(1))
                match = re.search(r'data-tab-item="repositories".*?class="Counter"[^>]*>(\d+)</span>', html)
                if match:
                    return int(match.group(1))
        except Exception as se:
            logger.debug("GitHub HTML scrape fallback failed for %s: %s", username, se)

    return 0


def validate_links_and_trust(resume_text: str) -> Dict[str, Any]:
    """Scan resume text for LinkedIn, GitHub, and portfolio URLs, verify them, and compute trust score."""
    if not resume_text:
        return {"trust_score": 50.0, "logs": ["Empty resume text"], "checked_urls": {}}

    logs = []
    checked_urls = {}

    # 1. Extract URLs
    linkedin_matches = list(set(re.findall(r"\b(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+\b", resume_text)))
    github_matches = list(set(re.findall(r"\b(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+\b", resume_text)))
    all_links = re.findall(r"\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-z]{2,6}(?:/[^\s]*)?\b", resume_text)

    other_links = []
    for link in all_links:
        link_lower = link.lower()
        if "linkedin.com" in link_lower or "github.com" in link_lower:
            continue
        if any(h in link_lower for h in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "example.com", "pdf", "docx"]):
            continue
        other_links.append(link)
    other_links = list(set(other_links))

    # Keep a max limit of urls checked to limit runtime overhead
    linkedin_matches = linkedin_matches[:2]
    github_matches = github_matches[:2]
    other_links = other_links[:3]

    base_score = 50.0
    modifications = 0.0
    timeout = getattr(settings.premium, "link_timeout", 5.0)

    # Validate LinkedIn
    has_linkedin = len(linkedin_matches) > 0
    for link in linkedin_matches:
        valid, status, msg = _ping_url(link, timeout)
        checked_urls[link] = {"type": "linkedin", "valid": valid, "status": status, "msg": msg}
        logs.append(f"LinkedIn [{link}]: {msg}")
        if valid:
            modifications += 15.0
        else:
            modifications -= 15.0

    # Validate GitHub
    has_github = len(github_matches) > 0
    for link in github_matches:
        valid, status, msg = _ping_url(link, timeout)
        checked_urls[link] = {"type": "github", "valid": valid, "status": status, "msg": msg}
        
        repos = 0
        if valid:
            modifications += 15.0
            repos = _get_github_repo_count(link)
            checked_urls[link]["repos"] = repos
            msg += f" | Public Repos: {repos}"
            if repos > 0:
                bonus = min(repos * 1.5, 15.0)
                modifications += bonus
                logs.append(f"GitHub [{link}]: {msg} (Bonus: +{bonus:.1f} pts)")
            else:
                logs.append(f"GitHub [{link}]: {msg}")
        else:
            modifications -= 15.0
            logs.append(f"GitHub [{link}]: {msg}")

    # Validate Portfolios
    for link in other_links:
        valid, status, msg = _ping_url(link, timeout)
        checked_urls[link] = {"type": "portfolio", "valid": valid, "status": status, "msg": msg}
        logs.append(f"Portfolio [{link}]: {msg}")
        if valid:
            modifications += 10.0
        else:
            modifications -= 10.0

    trust_score = base_score + modifications
    trust_score = max(0.0, min(100.0, trust_score))

    if not has_linkedin and not has_github and not other_links:
        logs.append("No portfolio, LinkedIn, or GitHub links found in resume.")

    return {
        "trust_score": round(trust_score, 1),
        "logs": logs,
        "checked_urls": checked_urls
    }
