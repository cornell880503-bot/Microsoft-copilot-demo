"""
Cross-platform active window detection + screen capture.

- Windows : win32gui (pywin32)
- macOS   : AppleScript via subprocess; screencapture for screenshot
- Linux   : xdotool via subprocess; scrot/import for screenshot
"""

import base64
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_active_window_title() -> Optional[str]:
    platform = sys.platform
    if platform == "win32":
        return _get_win32()
    elif platform == "darwin":
        return _get_macos()
    else:
        return _get_linux()


def capture_screen_base64() -> Optional[str]:
    """
    Capture the full screen and return as base64-encoded PNG.
    Returns None if screen capture is unavailable.
    """
    platform = sys.platform
    tmp = Path(tempfile.mktemp(suffix=".png"))
    try:
        if platform == "darwin":
            # macOS: screencapture -x (no sound) -t png
            subprocess.run(
                ["screencapture", "-x", "-t", "png", str(tmp)],
                check=True, timeout=5, capture_output=True,
            )
        elif platform == "linux":
            # Try scrot, fall back to gnome-screenshot
            try:
                subprocess.run(["scrot", str(tmp)], check=True, timeout=5, capture_output=True)
            except FileNotFoundError:
                subprocess.run(
                    ["gnome-screenshot", "-f", str(tmp)], check=True, timeout=5, capture_output=True
                )
        else:
            # Windows: use PIL if available
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(tmp), "PNG")

        data = tmp.read_bytes()
        logger.info("Screen captured: %d bytes", len(data))
        return base64.b64encode(data).decode()

    except Exception as e:
        logger.warning("Screen capture failed: %s", e)
        return None
    finally:
        if tmp.exists():
            tmp.unlink()


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
    set visibleApps to name of every application process whose visible is true
end tell
set prev to ""
repeat with appName in visibleApps
    if appName is not "Electron" and appName is not "loginwindow" and appName is not "Finder" then
        set prev to appName
        exit repeat
    end if
end repeat
if prev is "" then
    tell application "System Events"
        set prev to name of first application process whose frontmost is true
    end tell
end if
return prev
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
