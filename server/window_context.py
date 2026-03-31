"""
Cross-platform active window detection + screen capture.

- Windows : win32gui (pywin32)
- macOS   : AppleScript via subprocess; screencapture for screenshot
- Linux   : xdotool via subprocess; scrot/import for screenshot
"""

import base64
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Background app monitor (macOS) ───────────────────────────────────────────
# Continuously samples the frontmost app so we always know the last
# non-Electron app the user was in, even after Copilot steals focus.

_last_user_app: str = ""
_IGNORED = {"Electron", "loginwindow", "Finder", "Dock", "SystemUIServer", ""}

def _macos_frontmost() -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e",
             "tell application \"System Events\" to get name of first application process whose frontmost is true"],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return ""

def _background_monitor():
    global _last_user_app
    while True:
        app = _macos_frontmost()
        if app and app not in _IGNORED:
            _last_user_app = app
        time.sleep(1)

if sys.platform == "darwin":
    threading.Thread(target=_background_monitor, daemon=True).start()


def _display_env() -> dict:
    """Return env dict with DISPLAY set — required for X11 tools on Linux."""
    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":99"
    return env


def get_active_window_title() -> Optional[str]:
    platform = sys.platform
    if platform == "win32":
        return _get_win32()
    elif platform == "darwin":
        # Return last known user app from background monitor
        return _last_user_app or _macos_frontmost() or None
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
            # Hide Electron window so background app is fully visible
            subprocess.run(
                ["osascript", "-e", 'tell application "Electron" to set visible to false'],
                timeout=3, capture_output=True,
            )
            time.sleep(0.35)
            try:
                subprocess.run(
                    ["screencapture", "-x", "-t", "png", str(tmp)],
                    check=True, timeout=5, capture_output=True,
                )
            finally:
                # Always restore the window
                subprocess.run(
                    ["osascript", "-e", 'tell application "Electron" to set visible to true'],
                    timeout=3, capture_output=True,
                )
        elif platform == "linux":
            env = _display_env()
            try:
                subprocess.run(
                    ["scrot", str(tmp)], check=True, timeout=5, capture_output=True, env=env
                )
            except FileNotFoundError:
                subprocess.run(
                    ["gnome-screenshot", "-f", str(tmp)],
                    check=True, timeout=5, capture_output=True, env=env,
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
    set appStr to appName as string
    if appStr is not "Electron" and appStr is not "loginwindow" and appStr is not "Finder" then
        set prev to appStr
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
            capture_output=True, text=True, timeout=3,
            env=_display_env(),
        )
        title = result.stdout.strip()
        return title if title else None
    except FileNotFoundError:
        return _fallback("xdotool not found. Run: sudo apt install xdotool")
    except Exception as e:
        return _fallback(str(e))


def _fallback(reason: str) -> str:
    return f"[unavailable: {reason}]"
