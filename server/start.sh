#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Copilot Python Sidecar — startup script
# Run from the /server directory: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create virtualenv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install / sync dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# (Windows users: also run: pip install pywin32)

echo "Starting Copilot sidecar on http://localhost:8765 ..."
uvicorn main:app --host 127.0.0.1 --port 8765 --reload
