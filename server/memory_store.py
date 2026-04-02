from __future__ import annotations

import json
import re
from pathlib import Path


MEMORY_PATH = Path.home() / ".copilot" / "memory.json"


class MemoryStore:
    def __init__(self, path: Path | None = None):
        self.path = path or MEMORY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self.load()

    def load(self) -> dict:
        if not self.path.exists():
            return {"preferences": {}, "behavioral": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {
                "preferences": data.get("preferences", {}),
                "behavioral": data.get("behavioral", {}),
            }
        except Exception:
            return {"preferences": {}, "behavioral": {}}

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_preferences(self) -> dict:
        return dict(self.memory.get("preferences", {}))

    def update(self, key: str, value: str) -> None:
        self.memory.setdefault("preferences", {})[key] = value
        self.save()

    def delete(self, key: str) -> bool:
        preferences = self.memory.setdefault("preferences", {})
        if key not in preferences:
            return False
        del preferences[key]
        self.save()
        return True

    def maybe_update_from_user_input(self, user_input: str) -> dict:
        """
        Only capture explicit user instructions as durable memory.
        """
        updates: dict[str, str] = {}
        text = user_input.strip().lower()

        tone_patterns = [
            (r"\bkeep it concise\b", "concise"),
            (r"\bbe concise\b", "concise"),
            (r"\bbrief\b", "concise"),
            (r"簡潔", "concise"),
            (r"精簡", "concise"),
            (r"\bdetailed\b", "detailed"),
            (r"詳細", "detailed"),
        ]
        format_patterns = [
            (r"\bbullet points?\b", "bullet_points"),
            (r"條列", "bullet_points"),
            (r"\btable format\b", "table"),
            (r"\buse a table\b", "table"),
        ]

        for pattern, value in tone_patterns:
            if re.search(pattern, text):
                updates["tone"] = value
                break

        for pattern, value in format_patterns:
            if re.search(pattern, text):
                updates["format"] = value
                break

        for key, value in updates.items():
            self.update(key, value)
        return updates

