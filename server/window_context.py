"""
Cross-platform active window detection.

- Windows : win32gui (pywin32)
- macOS   : AppleScript via subprocess
- Linux   : xdotool via subprocess
"""

import subprocess
import sys
from typing import Optional


def get_active_window_title() -> Optional[str]:
    platform = sys.platform

    if platform == "win32":
        return _get_win32()
    elif platform == "darwin":
        return _get_macos()
    else:
        return _get_linux()


# ── Windows ──────────────────────────────────────────────────────────────────

def _get_win32() -> Optional[str]:
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return title or None
    except ImportError:
        return _fallback("pywin32 not installed. Run: pip install pywin32")
    except Exception as e:
        return _fallback(str(e))


# ── macOS ─────────────────────────────────────────────────────────────────────

_MACOS_SCRIPT = """\
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
end tell
return frontApp
"""

def _get_macos() -> Optional[str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", _MACOS_SCRIPT],
            capture_output=True, text=True, timeout=3
        )
        title = result.stdout.strip()
        return title if title else None
    except Exception as e:
        return _fallback(str(e))


# ── Linux ─────────────────────────────────────────────────────────────────────

def _get_linux() -> Optional[str]:
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3
        )
        title = result.stdout.strip()
        return title if title else None
    except FileNotFoundError:
        return _fallback("xdotool not found. Run: sudo apt install xdotool")
    except Exception as e:
        return _fallback(str(e))


def _fallback(reason: str) -> str:
    return f"[unavailable: {reason}]"
