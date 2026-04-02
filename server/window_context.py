"""
Cross-platform active window detection + screen capture.

- Windows : win32gui (pywin32)
- macOS   : AppleScript via subprocess; screencapture for screenshot
- Linux   : xdotool via subprocess; scrot/import for screenshot
"""

import base64
import json
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
_last_user_window: str = ""
_last_capture_mode: str = "unknown"
_IGNORED = {"Electron", "loginwindow", "Finder", "Dock", "SystemUIServer", ""}

def _macos_frontmost_app() -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e",
             "tell application \"System Events\" to get name of first application process whose frontmost is true"],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _macos_frontmost_window_title() -> str:
    try:
        script = """\
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    try
        set winName to name of front window of frontApp
    on error
        set winName to ""
    end try
end tell
return winName
"""
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _combine_app_window(app: str, window_title: str) -> str:
    app = (app or "").strip()
    window_title = (window_title or "").strip()
    if app and window_title and window_title.lower() != app.lower():
        return f"{app} — {window_title}"
    return app or window_title


def _macos_window_bounds(app: str) -> tuple[int, int, int, int] | None:
    app = (app or "").strip()
    if not app:
        return None
    script = f"""\
tell application "System Events"
    try
        tell application process "{app}"
            if (count of windows) is 0 then return ""
            set winPos to position of front window
            set winSize to size of front window
            return (item 1 of winPos as text) & "," & (item 2 of winPos as text) & "," & (item 1 of winSize as text) & "," & (item 2 of winSize as text)
        end tell
    on error
        return ""
    end try
end tell
"""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        raw = r.stdout.strip()
        if not raw:
            return None
        parts = [int(float(p.strip())) for p in raw.split(",")]
        if len(parts) != 4:
            return None
        x, y, w, h = parts
        if w <= 0 or h <= 0:
            return None
        return x, y, w, h
    except Exception:
        return None


def _macos_window_info(app: str) -> dict | None:
    app = (app or "").strip()
    if not app:
        return None
    script_path = Path(tempfile.mktemp(suffix=".swift"))
    script_path.write_text(
        """
import Foundation
import CoreGraphics

guard CommandLine.arguments.count > 1 else {
    fputs("missing app name\\n", stderr)
    exit(1)
}

let targetApp = CommandLine.arguments[1]
let windowList = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] ?? []

var best: [String: Any]? = nil
var bestArea: Double = -1

for window in windowList {
    guard let owner = window[kCGWindowOwnerName as String] as? String, owner == targetApp else { continue }
    let layer = window[kCGWindowLayer as String] as? Int ?? 0
    if layer != 0 { continue }
    guard let bounds = window[kCGWindowBounds as String] as? [String: Any] else { continue }
    let width = bounds["Width"] as? Double ?? 0
    let height = bounds["Height"] as? Double ?? 0
    let area = width * height
    if area > bestArea {
        bestArea = area
        best = [
            "window_id": window[kCGWindowNumber as String] as Any,
            "x": bounds["X"] as Any,
            "y": bounds["Y"] as Any,
            "width": width,
            "height": height
        ]
    }
}

guard let output = best else {
    print("")
    exit(0)
}

let data = try JSONSerialization.data(withJSONObject: output, options: [])
print(String(data: data, encoding: .utf8) ?? "")
""",
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            ["swift", str(script_path), app],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
        raw = result.stdout.strip()
        return json.loads(raw) if raw else None
    except Exception:
        return None
    finally:
        script_path.unlink(missing_ok=True)

def _macos_first_visible_non_electron() -> str:
    """Return the first visible non-Electron app — used at startup."""
    try:
        script = """\
tell application "System Events"
    set visibleApps to name of every application process whose visible is true
end tell
set prev to ""
repeat with appName in visibleApps
    set appStr to appName as string
    if appStr is not "Electron" and appStr is not "loginwindow" and appStr is not "Finder" and appStr is not "Dock" then
        set prev to appStr
        exit repeat
    end if
end repeat
return prev
"""
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        return r.stdout.strip()
    except Exception:
        return ""

def _background_monitor():
    global _last_user_app, _last_user_window
    while True:
        app = _macos_frontmost_app()
        if app and app not in _IGNORED:
            _last_user_app = app
            _last_user_window = _combine_app_window(app, _macos_frontmost_window_title())
        time.sleep(1)

if sys.platform == "darwin":
    # Pre-populate immediately so the first /get-active-window call is useful
    _initial = _macos_first_visible_non_electron()
    if _initial:
        _last_user_app = _initial
        _last_user_window = _combine_app_window(_initial, _macos_frontmost_window_title())
        logger.info("Initial user app: %s", _last_user_window)
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
        # Return last known user-facing window description from background monitor
        current_app = _last_user_app or _macos_frontmost_app()
        current_window = _last_user_window or _combine_app_window(current_app, _macos_frontmost_window_title())
        return current_window or current_app or None
    else:
        return _get_linux()


def get_last_capture_mode() -> str:
    return _last_capture_mode


def capture_screen_base64() -> Optional[str]:
    """
    Capture the target app window when possible and return as base64-encoded PNG.
    Falls back to full-screen capture if window bounds are unavailable.
    Returns None if screen capture is unavailable.
    """
    platform = sys.platform
    tmp = Path(tempfile.mktemp(suffix=".png"))
    global _last_capture_mode
    _last_capture_mode = "unknown"
    try:
        if platform == "darwin":
            target_app = _last_user_app or _macos_frontmost_app()
            window_info = _macos_window_info(target_app)
            bounds = _macos_window_bounds(target_app)
            try:
                if window_info and window_info.get("window_id"):
                    window_id = str(window_info["window_id"])
                    subprocess.run(
                        ["screencapture", "-x", "-l", window_id, "-t", "png", str(tmp)],
                        check=True, timeout=5, capture_output=True,
                    )
                    _last_capture_mode = "app-window"
                    logger.info("Captured app window by window id for %s: window_id=%s", target_app, window_id)
                elif bounds:
                    x, y, w, h = bounds
                    subprocess.run(
                        ["osascript", "-e", 'tell application "Electron" to set visible to false'],
                        timeout=3, capture_output=True,
                    )
                    time.sleep(0.2)
                    subprocess.run(
                        ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", "-t", "png", str(tmp)],
                        check=True, timeout=5, capture_output=True,
                    )
                    _last_capture_mode = "app-window"
                    logger.info("Captured app window region for %s: x=%s y=%s w=%s h=%s", target_app, x, y, w, h)
                else:
                    subprocess.run(
                        ["screencapture", "-x", "-t", "png", str(tmp)],
                        check=True, timeout=5, capture_output=True,
                    )
                    _last_capture_mode = "full-screen"
                    logger.info("Captured full screen because window bounds were unavailable for %s", target_app or "<unknown>")
            finally:
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
                _last_capture_mode = "full-screen"
            except FileNotFoundError:
                subprocess.run(
                    ["gnome-screenshot", "-f", str(tmp)],
                    check=True, timeout=5, capture_output=True, env=env,
                )
                _last_capture_mode = "full-screen"
        else:
            # Windows: use PIL if available
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(tmp), "PNG")
            _last_capture_mode = "full-screen"

        data = tmp.read_bytes()
        logger.info("Screen captured: %d bytes", len(data))
        return base64.b64encode(data).decode()

    except Exception as e:
        logger.warning("Screen capture failed: %s", e)
        return None
    finally:
        if tmp.exists():
            tmp.unlink()


# ── Active document text extraction ──────────────────────────────────────────

_APP_DOC_SCRIPTS = {
    "Preview":         'tell application "Preview" to get path of document 1',
    "Adobe Acrobat":   'tell application "Adobe Acrobat" to get path of document 1',
    "AdobeAcrobat":    'tell application "Adobe Acrobat" to get path of document 1',
    "Microsoft Excel": 'tell application "Microsoft Excel" to get full name of active workbook',
    "Microsoft Word":  'tell application "Microsoft Word" to get full name of active document',
    "Microsoft PowerPoint": 'tell application "Microsoft PowerPoint" to get full name of active presentation',
    "Numbers":         'tell application "Numbers" to get path of document 1',
    "Pages":           'tell application "Pages" to get path of document 1',
    "Keynote":         'tell application "Keynote" to get path of document 1',
}

def _get_document_path_from_app(app: str) -> Optional[str]:
    script = _APP_DOC_SCRIPTS.get(app)
    if not script:
        return None
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        path = r.stdout.strip()
        if path and Path(path).exists():
            return path
    except Exception:
        pass
    return None

def _extract_text_from_file(path: str, max_chars: int = 6000) -> Optional[str]:
    try:
        ext = Path(path).suffix.lower()
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:15])
            return text.strip()[:max_chars] or None
        elif ext in (".xlsx", ".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            rows = ["\t".join(str(v) if v is not None else "" for v in row)
                    for row in ws.iter_rows(values_only=True)]  # all rows, no limit
            return "\n".join(rows).strip()[:50000] or None
        elif ext == ".csv":
            # Read full file for data analysis; 50k chars ~covers most datasets
            return Path(path).read_text(encoding="utf-8", errors="ignore")[:50000]
        elif ext in (".docx",):
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs).strip()[:max_chars] or None
        elif ext in (".txt", ".md"):
            return Path(path).read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception as e:
        logger.warning("Text extraction failed for %s: %s", path, e)
    return None

def get_active_document_content() -> tuple[Optional[str], Optional[str]]:
    """
    Returns (doc_text, file_path) for the document open in the active app.
    Returns (None, None) if not available or not on macOS.
    """
    if sys.platform != "darwin":
        return None, None
    app = _last_user_app
    if not app:
        return None, None
    path = _get_document_path_from_app(app)
    if not path:
        return None, None
    text = _extract_text_from_file(path)
    if text:
        logger.info("Extracted %d chars from %s (%s)", len(text), Path(path).name, app)
    return text, path

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
