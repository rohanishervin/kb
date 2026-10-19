#!/usr/bin/env bash
set -e

# KB command line (log practice, see queue, tag)
# Runs kb.py using the project's virtual environment or uv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python kb.py "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run kb.py "$@"
else
    exec python3 kb.py "$@"
fi
