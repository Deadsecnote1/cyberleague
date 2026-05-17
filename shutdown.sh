#!/usr/bin/env bash
# Cyber League — stop n8n, portal, active scans, and related background workers.
#
# Usage:
#   ./shutdown.sh              # graceful stop (SIGTERM, then SIGKILL if needed)
#   CYBERLEAGUE_SHUTDOWN_DRY=1 ./shutdown.sh   # print what would be stopped
#
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SCAN_ROOT="${ROOT}/scans"
PORTAL_PORT="${CYBERLEAGUE_PORTAL_PORT:-8765}"
N8N_PORT="${CYBERLEAGUE_N8N_PORT:-5678}"
WAIT_SEC="${CYBERLEAGUE_SHUTDOWN_WAIT:-8}"
DRY="${CYBERLEAGUE_SHUTDOWN_DRY:-0}"

declare -a STOPPED=()
declare -a SKIPPED=()

log() { echo "$*"; }

dry_run() { [[ "$DRY" == "1" ]]; }

record() {
  STOPPED+=("$1")
  if dry_run; then
    log "  [dry-run] would stop: $1"
  else
    log "  ✓ stopped: $1"
  fi
}

# Collect unique PIDs (best-effort).
pids_on_port() {
  local port="$1"
  local pid
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' || true
  elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -E ":${port}\\b" | sed -n 's/.*pid=\\([0-9]*\\).*/\\1/p' || true
  fi
}

pids_matching() {
  local pattern="$1"
  pgrep -f "$pattern" 2>/dev/null || true
}

# SIGTERM children first, then parent; optional SIGKILL pass.
kill_pids() {
  local signal="$1"
  shift
  local pid
  for pid in "$@"; do
    [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] || continue
    kill -0 "$pid" 2>/dev/null || continue
    if dry_run; then
      log "    kill -$signal $pid ($(ps -p "$pid" -o args= 2>/dev/null | head -c 120))"
      continue
    fi
    kill "-$signal" "$pid" 2>/dev/null || true
  done
}

stop_pid_list() {
  local label="$1"
  shift
  local -a pids=("$@")
  local -a uniq=()
  local pid

  if [[ ${#pids[@]} -eq 0 ]]; then
    SKIPPED+=("$label (not running)")
    return 0
  fi

  # Deduplicate
  for pid in "${pids[@]}"; do
    [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] || continue
    local seen=0
    for u in "${uniq[@]}"; do
      [[ "$u" == "$pid" ]] && seen=1 && break
    done
    [[ "$seen" -eq 0 ]] && uniq+=("$pid")
  done

  if [[ ${#uniq[@]} -eq 0 ]]; then
    SKIPPED+=("$label (not running)")
    return 0
  fi

  # Children before parents
  local -a children=()
  for pid in "${uniq[@]}"; do
    while read -r child; do
      [[ -n "$child" ]] && children+=("$child")
    done < <(pgrep -P "$pid" 2>/dev/null || true)
  done

  kill_pids TERM "${children[@]}" "${uniq[@]}"

  if ! dry_run; then
    local i
    for ((i = 0; i < WAIT_SEC; i++)); do
      local alive=0
      for pid in "${uniq[@]}"; do
        kill -0 "$pid" 2>/dev/null && alive=1 && break
      done
      [[ "$alive" -eq 0 ]] && break
      sleep 1
    done
    local -a still=()
    for pid in "${uniq[@]}"; do
      kill -0 "$pid" 2>/dev/null && still+=("$pid")
    done
    if [[ ${#still[@]} -gt 0 ]]; then
      kill_pids KILL "${still[@]}"
      sleep 1
    fi
  fi

  record "$label (${#uniq[@]} process(es))"
}

request_scan_stop() {
  local wd
  if [[ ! -d "$SCAN_ROOT" ]]; then
    return 0
  fi
  for wd in "$SCAN_ROOT"/*; do
    [[ -d "$wd" ]] || continue
    if dry_run; then
      log "  [dry-run] would touch ${wd}/.scan_stop"
    else
      touch "${wd}/.scan_stop" 2>/dev/null || true
    fi
  done
}

stop_active_scans() {
  log "→ Active scan workers"
  request_scan_stop

  local -a scan_pids=()
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] && scan_pids+=("$pid")
  done < <(pids_matching "${ROOT}/scripts/bugbounty-scan\\.sh")
  while read -r pid; do
    [[ -n "$pid" ]] && scan_pids+=("$pid")
  done < <(pids_matching "${ROOT}/scans/")
  while read -r pid; do
    [[ -n "$pid" ]] && scan_pids+=("$pid")
  done < <(pids_matching "${ROOT}/scripts/scan_subdomains\\.py")
  while read -r pid; do
    [[ -n "$pid" ]] && scan_pids+=("$pid")
  done < <(pids_matching "${ROOT}/scripts/rate_limit_guard\\.py")

  stop_pid_list "scan tools / bugbounty-scan.sh" "${scan_pids[@]}"
}

stop_portal() {
  log "→ Cyber League portal (127.0.0.1:${PORTAL_PORT})"
  local -a pids=()
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_on_port "$PORTAL_PORT")
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "uvicorn portal\\.app:app.*--host 127\\.0\\.0\\.1.*--port ${PORTAL_PORT}")
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "${ROOT}/\\.venv-portal/.*/uvicorn portal\\.app")
  stop_pid_list "portal (uvicorn)" "${pids[@]}"
}

stop_n8n() {
  log "→ n8n engine (localhost:${N8N_PORT})"
  local -a pids=()
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_on_port "$N8N_PORT")
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "n8n start")
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "@n8n/task-runner")
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "n8n.*${ROOT}")
  stop_pid_list "n8n + task runners" "${pids[@]}"
}

stop_launcher() {
  log "→ cyberleague.sh wrapper (if still running)"
  local -a pids=()
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pids_matching "${ROOT}/cyberleague\\.sh")
  stop_pid_list "cyberleague.sh" "${pids[@]}"
}

port_in_use() {
  local port="$1"
  if command -v curl >/dev/null 2>&1; then
    if [[ "$port" == "$PORTAL_PORT" ]]; then
      curl -sf "http://127.0.0.1:${port}/health" >/dev/null 2>&1 && return 0
    fi
    if [[ "$port" == "$N8N_PORT" ]]; then
      curl -sf "http://localhost:${port}/healthz" >/dev/null 2>&1 && return 0
    fi
  fi
  [[ -n "$(pids_on_port "$port" | head -1)" ]]
}

banner() {
  echo ""
  echo "  ╔═══════════════════════════════════════╗"
  echo "  ║        CYBER  LEAGUE  SHUTDOWN        ║"
  echo "  ╚═══════════════════════════════════════╝"
  echo ""
  if dry_run; then
    echo "  (dry-run — no processes will be killed)"
    echo ""
  fi
}

summary() {
  echo ""
  if [[ ${#STOPPED[@]} -gt 0 ]]; then
    log "Stopped:"
    for s in "${STOPPED[@]}"; do
      log "  • $s"
    done
  fi
  if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    log "Already down:"
    for s in "${SKIPPED[@]}"; do
      log "  • $s"
    done
  fi
  echo ""
  if dry_run; then
    log "Re-run without CYBERLEAGUE_SHUTDOWN_DRY=1 to apply."
    return 0
  fi
  if port_in_use "$PORTAL_PORT"; then
    log "Warning: portal port ${PORTAL_PORT} still in use."
  else
    log "Portal port ${PORTAL_PORT} is free."
  fi
  if port_in_use "$N8N_PORT"; then
    log "Warning: n8n port ${N8N_PORT} still in use."
  else
    log "n8n port ${N8N_PORT} is free."
  fi
  echo ""
}

main() {
  banner
  # Scans first so n8n does not respawn workers mid-shutdown.
  stop_active_scans
  stop_portal
  stop_n8n
  stop_launcher
  summary
}

main "$@"
