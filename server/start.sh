#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Copilot Python Sidecar — startup script
# Run from the /server directory: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Python version check ──────────────────────────────────────────────────────
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PY_VERSION detected"

# ── Create virtualenv ─────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# ── Apple Silicon: install onnxruntime-silicon before chromadb ────────────────
# The standard `onnxruntime` package has no ARM64 wheels.
# `onnxruntime-silicon` provides the Apple M-series compatible build.
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
