#!/usr/bin/env bash
# Cyber League — start n8n engine + local portal (one command for the full pentest workflow).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export NODES_EXCLUDE='[]'
export NODE_FUNCTION_ALLOW_BUILTIN='fs,path,os,crypto,util'

N8N_URL="http://localhost:5678"
PORTAL_URL="http://127.0.0.1:8765"
LOG_DIR="${ROOT}/logs"
VENV="${ROOT}/.venv-portal"
N8N_PID=""
PORTAL_PID=""

mkdir -p "$LOG_DIR"

banner() {
  echo ""
  echo "  ╔═══════════════════════════════════════╗"
  echo "  ║           CYBER  LEAGUE               ║"
  echo "  ║   Bug bounty pipeline · local stack   ║"
  echo "  ╚═══════════════════════════════════════╝"
  echo ""
}

stop_children() {
  local pid
  for pid in "$N8N_PID" "$PORTAL_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  # Child processes (task runner, uvicorn workers)
  pkill -P "$N8N_PID" 2>/dev/null || true
  pkill -P "$PORTAL_PID" 2>/dev/null || true
}

cleanup() {
  echo ""
  echo "Shutting down Cyber League..."
  stop_children
  wait "$N8N_PID" 2>/dev/null || true
  wait "$PORTAL_PID" 2>/dev/null || true
  echo "Stopped."
}

trap cleanup EXIT INT TERM

wait_for_url() {
  local url="$1"
  local name="$2"
  local max="${3:-60}"
  local i
  for ((i = 1; i <= max; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  ✓ $name ready"
      return 0
    fi
    sleep 1
  done
  echo "  ✗ $name did not become ready ($url)" >&2
  return 1
}

ensure_portal_venv() {
  if [[ ! -d "$VENV" ]]; then
    echo "Creating portal virtualenv..."
    python3 -m venv "$VENV"
  fi
  if [[ ! -x "$VENV/bin/uvicorn" ]]; then
    echo "Installing portal dependencies..."
    "$VENV/bin/pip" install -q -r "$ROOT/portal/requirements.txt"
  fi
}

# Avoid duplicate stacks unless forced
if pgrep -f "n8n start" >/dev/null 2>&1 && [[ "${CYBERLEAGUE_FORCE:-}" != "1" ]]; then
  echo "n8n already running. Set CYBERLEAGUE_FORCE=1 to start another instance." >&2
  exit 1
fi
if pgrep -f "uvicorn portal.app:app" >/dev/null 2>&1 && [[ "${CYBERLEAGUE_FORCE:-}" != "1" ]]; then
  echo "Portal already running. Set CYBERLEAGUE_FORCE=1 to start another instance." >&2
  exit 1
fi

banner
echo "Starting services (logs in ${LOG_DIR}/)..."
echo ""

ensure_portal_venv

echo "→ n8n engine"
n8n start >>"${LOG_DIR}/n8n.log" 2>&1 &
N8N_PID=$!

echo "→ Cyber League portal"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m uvicorn portal.app:app --host 127.0.0.1 --port 8765 >>"${LOG_DIR}/portal.log" 2>&1 &
PORTAL_PID=$!

wait_for_url "${N8N_URL}/healthz" "n8n" 90
wait_for_url "${PORTAL_URL}/health" "portal" 30

echo ""
echo "  Portal:  ${PORTAL_URL}"
echo "  n8n:     ${N8N_URL}"
echo "  Logs:    ${LOG_DIR}/n8n.log  ${LOG_DIR}/portal.log"
echo ""
echo "  Press Ctrl+C to stop both services."
echo ""

# Keep script alive until children exit or user interrupts
while kill -0 "$N8N_PID" 2>/dev/null || kill -0 "$PORTAL_PID" 2>/dev/null; do
  if ! kill -0 "$N8N_PID" 2>/dev/null; then
    echo "n8n exited unexpectedly. See ${LOG_DIR}/n8n.log" >&2
    exit 1
  fi
  if ! kill -0 "$PORTAL_PID" 2>/dev/null; then
    echo "Portal exited unexpectedly. See ${LOG_DIR}/portal.log" >&2
    exit 1
  fi
  sleep 2
done
