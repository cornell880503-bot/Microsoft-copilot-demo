"""
Persistent conversation storage.
Each chat is stored as a JSON file in ~/.copilot/chats/{chat_id}.json
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

CHATS_DIR = Path.home() / ".copilot" / "chats"


def _ensure_dir() -> None:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def list_chats() -> list[dict]:
    _ensure_dir()
    chats = []
    for f in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            chats.append({
                "id":         data["id"],
                "title":      data.get("title", "Untitled"),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            pass
    return sorted(chats, key=lambda x: x["updated_at"], reverse=True)


def create_chat() -> dict:
    _ensure_dir()
    chat_id = f"chat_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    chat = {
        "id":         chat_id,
        "title":      "New Chat",
        "created_at": now,
        "updated_at": now,
        "messages":   [],
    }
    (CHATS_DIR / f"{chat_id}.json").write_text(
        json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return chat


def get_chat(chat_id: str) -> dict | None:
    path = CHATS_DIR / f"{chat_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_messages(chat_id: str, messages: list[dict]) -> tuple[dict | None, bool]:
    """
    Append messages and update updated_at.
    Returns (chat_metadata, was_first_message).
    Title is NOT auto-set here — caller should call update_title() with a summary.
    """
    path = CHATS_DIR / f"{chat_id}.json"
    if not path.exists():
        return None, False
    chat = json.loads(path.read_text(encoding="utf-8"))
    was_first = len(chat["messages"]) == 0
    now = datetime.now().isoformat()
    for msg in messages:
        entry = {
            "role":      msg["role"],
            "content":   msg["content"],
            "timestamp": now,
        }
        if msg.get("pipeline"):
            entry["pipeline"] = msg["pipeline"]
        chat["messages"].append(entry)
    chat["updated_at"] = now
    path.write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": chat["id"], "title": chat["title"], "updated_at": chat["updated_at"]}, was_first


def set_last_pipeline(chat_id: str, pipeline: list) -> None:
    """Attach pipeline log to the last assistant message."""
    path = CHATS_DIR / f"{chat_id}.json"
    if not path.exists():
        return
    chat = json.loads(path.read_text(encoding="utf-8"))
    # Find last assistant message and set its pipeline
    for msg in reversed(chat["messages"]):
        if msg["role"] == "assistant":
            msg["pipeline"] = pipeline
            break
    path.write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")


def update_title(chat_id: str, title: str) -> None:
    path = CHATS_DIR / f"{chat_id}.json"
    if not path.exists():
        return
    chat = json.loads(path.read_text(encoding="utf-8"))
    chat["title"] = title.strip()[:80] or "New Chat"
    chat["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_chat(chat_id: str) -> None:
    path = CHATS_DIR / f"{chat_id}.json"
    if path.exists():
        path.unlink()
