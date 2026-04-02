from __future__ import annotations

import json
from pathlib import Path


PRIVACY_MODE_PATH = Path.home() / ".copilot" / "privacy_mode.json"
SAFE_MODE = "safe"
ENHANCED_MODE = "enhanced"
VALID_MODES = {SAFE_MODE, ENHANCED_MODE}


def _default_payload() -> dict:
    return {
        "mode": SAFE_MODE,
        "screen_context_opt_in": False,
        "scope": "proactive_suggestions_only",
    }


def load_privacy_mode() -> dict:
    PRIVACY_MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PRIVACY_MODE_PATH.exists():
        return _default_payload()
    try:
        data = json.loads(PRIVACY_MODE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_payload()
    mode = data.get("mode", SAFE_MODE)
    if mode not in VALID_MODES:
        mode = SAFE_MODE
    return {
        "mode": mode,
        "screen_context_opt_in": mode == ENHANCED_MODE,
        "scope": data.get("scope", "proactive_suggestions_only"),
    }


def save_privacy_mode(mode: str) -> dict:
    normalized = (mode or SAFE_MODE).strip().lower()
    if normalized not in VALID_MODES:
        normalized = SAFE_MODE
    payload = {
        "mode": normalized,
        "screen_context_opt_in": normalized == ENHANCED_MODE,
        "scope": "proactive_suggestions_only",
    }
    PRIVACY_MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRIVACY_MODE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return payload
