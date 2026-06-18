"""Safety and Security Guardrails for PSI Resume Analyser."""

import logging
import re
from typing import Dict, Tuple

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
