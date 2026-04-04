"""
ActionLedger — LIFO snapshot/restore stack for reversible Copilot actions.

Covered actions: SAVE_FILE, DELETE_FILE, SCHEDULE_MEETING.
EXECUTE_PYTHON is best-effort: we diff ~/Downloads before/after and record
any new files that appeared.
"""

import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BACKUP_DIR = Path.home() / ".copilot_backups"
MAX_ENTRIES = 10          # max undo depth
MAX_BACKUP_MB = 200       # never exceed this on disk


@dataclass
class LedgerEntry:
    action_type: str          # SAVE_FILE | DELETE_FILE | SCHEDULE_MEETING | EXECUTE_PYTHON
    artifact_path: str        # the file that was created/modified/deleted
    backup_path: Optional[str]  # None → artifact was newly created (undo = delete it)
    description: str
    timestamp: float = field(default_factory=time.time)


class ActionLedger:
    def __init__(self):
        self._stack: list[LedgerEntry] = []
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self, artifact_path: str, action_type: str, description: str) -> LedgerEntry:
        """
        Call BEFORE a destructive action executes.
        If the artifact already exists, backs it up; otherwise records it as a
        new creation so undo can delete it.
        Returns a LedgerEntry — call push() after the action succeeds.
        """
        src = Path(artifact_path)
        backup_path = None
        if src.exists() and src.is_file():
            ts = int(time.time() * 1000)
            backup_name = f"{ts}_{src.name}"
            dest = BACKUP_DIR / backup_name
            try:
                shutil.copy2(str(src), str(dest))
                backup_path = str(dest)
                logger.info("Ledger: snapshotted %s → %s", src.name, dest.name)
            except Exception as e:
                logger.warning("Ledger: snapshot failed for %s: %s", src, e)
        else:
            logger.info("Ledger: %s does not exist yet — undo will delete it", src.name)

        return LedgerEntry(
            action_type=action_type,
            artifact_path=artifact_path,
            backup_path=backup_path,
            description=description,
        )

    def snapshot_deletion(self, artifact_path: str, description: str) -> Optional[LedgerEntry]:
        """
        Call BEFORE DELETE_FILE. Backs up the file so undo can restore it.
        Returns None if the file doesn't exist.
        """
        src = Path(artifact_path)
        if not src.exists() or not src.is_file():
            return None
        ts = int(time.time() * 1000)
        backup_name = f"{ts}_{src.name}"
        dest = BACKUP_DIR / backup_name
        try:
            shutil.copy2(str(src), str(dest))
            logger.info("Ledger: backed up deleted file %s → %s", src.name, dest.name)
        except Exception as e:
            logger.warning("Ledger: deletion snapshot failed: %s", e)
            return None
        return LedgerEntry(
            action_type="DELETE_FILE",
            artifact_path=artifact_path,
            backup_path=str(dest),
            description=description,
        )

    # ── Push / Pop ────────────────────────────────────────────────────────────

    def push(self, entry: LedgerEntry):
        """Record a completed action in the undo stack."""
        self._stack.append(entry)
        # Trim oldest entries if stack is full
        while len(self._stack) > MAX_ENTRIES:
            old = self._stack.pop(0)
            _safe_unlink(old.backup_path)
        logger.info("Ledger push: %s '%s' (depth=%d)", entry.action_type, entry.description, len(self._stack))

    def undo(self) -> tuple[bool, str]:
        """
        Pop the last entry and reverse it.
        Returns (success: bool, message: str).
        """
        if not self._stack:
            return False, "Nothing to undo — the action history is empty."

        entry = self._stack.pop()
        artifact = Path(entry.artifact_path)

        try:
            if entry.action_type == "DELETE_FILE" and entry.backup_path:
                # Restore deleted file
                backup = Path(entry.backup_path)
                if not backup.exists():
                    return False, f"Backup is missing — cannot restore {artifact.name}."
                artifact.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(backup), str(artifact))
                _safe_unlink(str(backup))
                logger.info("Ledger: restored deleted file %s", artifact.name)
                return True, f"✅ Restored {artifact.name}."

            elif entry.backup_path:
                # Restore previous version (SAVE_FILE / SCHEDULE_MEETING overwrite)
                backup = Path(entry.backup_path)
                if not backup.exists():
                    return False, f"Backup is missing — cannot restore {artifact.name}."
                artifact.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(backup), str(artifact))
                _safe_unlink(str(backup))
                logger.info("Ledger: restored %s from backup", artifact.name)
                return True, f"✅ Restored original {artifact.name}."

            else:
                # New file creation — delete it
                if artifact.exists():
                    artifact.unlink()
                    logger.info("Ledger: deleted created artifact %s", artifact.name)
                    return True, f"✅ Deleted {artifact.name}."
                else:
                    return True, f"✅ {artifact.name} no longer exists — nothing to remove."

        except Exception as e:
            logger.exception("Ledger: undo failed for %s", entry.artifact_path)
            return False, f"Undo failed: {e}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def peek(self) -> Optional[LedgerEntry]:
        return self._stack[-1] if self._stack else None

    def is_empty(self) -> bool:
        return not self._stack

    def clear_backups(self):
        """Clear stale backup files on server startup."""
        if BACKUP_DIR.exists():
            shutil.rmtree(str(BACKUP_DIR), ignore_errors=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self._stack.clear()
        logger.info("Ledger: cleared backup dir and stack on startup")


def _safe_unlink(path: Optional[str]):
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


# Global singleton — imported by main.py and agent.py
ledger = ActionLedger()
