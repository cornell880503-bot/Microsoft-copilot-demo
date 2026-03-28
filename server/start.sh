#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Copilot Python Sidecar — startup script
# Run from the /server directory: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Require Python 3.12 ───────────────────────────────────────────────────────
# Python 3.13+ is not yet supported by chromadb / onnxruntime / torch.
# Install 3.12 with: brew install python@3.12
find_python() {
  for cmd in python3.12 python3.11 python3.10; do
    if command -v "$cmd" &>/dev/null; then
      local ver
      ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      local major minor
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
  echo "ERROR: Python 3.10–3.12 is required."
  echo "  chromadb and onnxruntime do not yet ship wheels for Python 3.13+."
  echo ""
  echo "Install Python 3.12 with Homebrew:"
  echo "  brew install python@3.12"
  echo ""
  echo "Then re-run: bash start.sh"
  exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PY_VERSION ($PYTHON)"

# ── Create virtualenv ─────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

# ── Apple Silicon: install onnxruntime-silicon before chromadb ────────────────
if [[ "$(uname -m)" == "arm64" && "$(uname -s)" == "Darwin" ]]; then
  echo "Apple Silicon detected — installing onnxruntime-silicon..."
  pip install -q onnxruntime-silicon
fi

# ── Install dependencies ──────────────────────────────────────────────────────
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting Copilot sidecar on http://127.0.0.1:8765 ..."
uvicorn main:app --host 127.0.0.1 --port 8765 --reload
