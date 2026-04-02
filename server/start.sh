#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Copilot Python Sidecar — startup script
# Run from the /server directory: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Require Python 3.10–3.12 ─────────────────────────────────────────────────
find_python() {
  for cmd in python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null; then
      local ver major minor
      ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      major=$(echo "$ver" | cut -d. -f1)
      minor=$(echo "$ver" | cut -d. -f2)
      if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ] && [ "$minor" -le 12 ]; then
        echo "$cmd"
        return
      fi
    fi
  done
  echo ""
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
  echo ""
  echo "ERROR: Python 3.10–3.12 is required (3.13+ not yet supported by chromadb/onnxruntime)."
  echo "Install with: brew install python@3.12"
  exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PY_VERSION ($PYTHON)"

# ── Reclaim the sidecar port if a previous instance is still running ─────────
PORT="${SIDECAR_PORT:-8765}"
EXISTING_PIDS="$(lsof -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
if [ -n "$EXISTING_PIDS" ]; then
  echo "Port $PORT is already in use. Stopping previous sidecar process(es): $EXISTING_PIDS"
  kill $EXISTING_PIDS 2>/dev/null || true
  sleep 1
  STILL_RUNNING="$(lsof -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
  if [ -n "$STILL_RUNNING" ]; then
    echo "Port $PORT is still busy. Force stopping: $STILL_RUNNING"
    kill -9 $STILL_RUNNING 2>/dev/null || true
    sleep 1
  fi
fi

# ── Create virtualenv ─────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

# ── Tesseract OCR (required for PNG/JPG indexing) ─────────────────────────────
if ! command -v tesseract &>/dev/null; then
  echo ""
  echo "Note: Tesseract not found — PNG/JPG files will be skipped."
  echo "      To enable image OCR: brew install tesseract"
  echo ""
fi

# ── Install dependencies ──────────────────────────────────────────────────────
echo "Installing dependencies (first run downloads ~300MB of ML models)..."
pip install -q -r requirements.txt

echo ""
echo "Starting Copilot sidecar on http://127.0.0.1:${PORT} ..."
uvicorn main:app --host 127.0.0.1 --port "$PORT" --reload
