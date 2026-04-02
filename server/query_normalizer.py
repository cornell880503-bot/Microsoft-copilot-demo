from __future__ import annotations

import re


_REPLACEMENTS = [
    (r"\bmtg\b", "meeting"),
    (r"\bmtgs\b", "meetings"),
    (r"\bappt\b", "appointment"),
    (r"\btmrw\b", "tomorrow"),
    (r"\bpls\b", "please"),
]


def normalize_query(text: str) -> str:
    normalized = (text or "").strip().lower()
    for pattern, replacement in _REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
