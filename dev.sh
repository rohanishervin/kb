#!/usr/bin/env bash
set -e

# KB Development One-Command Runner
# Runs dev.py using the project's virtual environment or uv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python dev.py "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run dev.py "$@"
else
    exec python3 dev.py "$@"
fi
