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


def append_messages(chat_id: str, messages: list[dict]) -> dict | None:
    """Append messages and update title / updated_at. Returns updated chat metadata."""
    path = CHATS_DIR / f"{chat_id}.json"
    if not path.exists():
        return None
    chat = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.now().isoformat()
    for msg in messages:
        chat["messages"].append({
            "role":      msg["role"],
            "content":   msg["content"],
            "timestamp": now,
        })
    chat["updated_at"] = now
    # Auto-title from first user message
    if chat["title"] == "New Chat":
        for msg in chat["messages"]:
            if msg["role"] == "user":
                t = msg["content"]
                chat["title"] = t[:48] + ("…" if len(t) > 48 else "")
                break
    path.write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"id": chat["id"], "title": chat["title"], "updated_at": chat["updated_at"]}


def delete_chat(chat_id: str) -> None:
    path = CHATS_DIR / f"{chat_id}.json"
    if path.exists():
        path.unlink()
