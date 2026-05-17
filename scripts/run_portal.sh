#!/usr/bin/env bash
# Local-only pentest dashboard (127.0.0.1:8765)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv-portal"

if [[ ! -d "$VENV" ]]; then
  echo "Creating portal virtualenv..."
  python3 -m venv "$VENV"
fi
if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "Installing portal dependencies..."
  "$VENV/bin/pip" install -q -r "$ROOT/portal/requirements.txt"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
echo "Starting portal at http://127.0.0.1:8765"
echo "Press Ctrl+C to stop."
exec python -m uvicorn portal.app:app --host 127.0.0.1 --port 8765
