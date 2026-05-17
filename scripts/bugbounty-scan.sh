#!/usr/bin/env bash
# Scan ONE intentionally vulnerable / authorized target.
# Usage: SCAN_PROFILE=both bash bugbounty-scan.sh <domain>
# SCAN_PROFILE: light | deep | both
set -euo pipefail

DOMAIN="${1:-}"
ROOT="/home/thanushiyan/Desktop/buildathon_cursor"
SCAN_PROFILE="${SCAN_PROFILE:-light}"
if [[ -f "${ROOT}/.current_scan_env" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ROOT}/.current_scan_env"
  set +a
fi
if [[ -z "$DOMAIN" || "$DOMAIN" == "undefined" ]] && [[ -f "${ROOT}/.current_scan_domain" ]]; then
  DOMAIN="$(head -1 "${ROOT}/.current_scan_domain" | tr -d '[:space:]')"
fi
SCAN_ROOT="${ROOT}/scans"
WORDLIST="${WORDLIST:-${ROOT}/wordlists/ffuf-quick.txt}"
THREADS="${THREADS:-40}"
FFUF_MAXTIME="${FFUF_MAXTIME:-90}"
FFUF_MATCH_CODES="${FFUF_MATCH_CODES:-200,204,301,302,307,401,403}"
NMAP_PORTS="${NMAP_PORTS:-top-100}"
NUCLEI_TAGS="${NUCLEI_TAGS:-cve,vuln,misconfig,exposure,tech,panel,default-logins,takeover,token,graphql,sqli}"
SQLI_SCAN="${SQLI_SCAN:-1}"
SQLI_MAX_URLS="${SQLI_MAX_URLS:-12}"
SQLI_TIMEOUT="${SQLI_TIMEOUT:-120}"
NUCLEI_SEVERITY="${NUCLEI_SEVERITY:-medium,high,critical}"
NUCLEI_TIMEOUT="${NUCLEI_TIMEOUT:-180}"
NIKTO_TIMEOUT="${NIKTO_TIMEOUT:-90}"
NMAP_SCRIPTS="${NMAP_SCRIPTS:-http-security-headers,http-enum,ssl-cert,ssl-enum-ciphers}"
SCAN_ALL_SUBDOMAINS="${SCAN_ALL_SUBDOMAINS:-1}"
MAX_SUBDOMAIN_SCANS="${MAX_SUBDOMAIN_SCANS:-5}"
PER_HOST_NUCLEI_TIMEOUT="${PER_HOST_NUCLEI_TIMEOUT:-60}"
FFUF_PER_HOST="${FFUF_PER_HOST:-0}"
NUCLEI_PER_HOST="${NUCLEI_PER_HOST:-0}"
SCAN_MAX_RUNTIME_MINUTES="${SCAN_MAX_RUNTIME_MINUTES:-0}"
NMAP_APEX_PORTS="${NMAP_APEX_PORTS:-80,443}"
REQUEST_DELAY_MS="${REQUEST_DELAY_MS:-500}"
REQUESTS_PER_MINUTE="${REQUESTS_PER_MINUTE:-30}"
BLOCK_CONSECUTIVE_THRESHOLD="${BLOCK_CONSECUTIVE_THRESHOLD:-3}"
GUARD_PY="${ROOT}/scripts/rate_limit_guard.py"

if [[ -z "$DOMAIN" ]]; then
  echo '{"ok":false,"error":"domain argument required"}'
  exit 1
fi

if [[ ! "$SCAN_PROFILE" =~ ^(light|deep|both)$ ]]; then
  printf '{"ok":false,"error":"invalid SCAN_PROFILE: %s"}\n' "$SCAN_PROFILE"
  exit 1
fi

DOMAIN="$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | sed -E 's#^https?://##; s#^www\.##; s#/.*##')"
SCOPE_FILE="${ROOT}/.current_scan_scope.json"
if [[ -f "$SCOPE_FILE" ]]; then
  if ! python3 -c "
import json, sys
from pathlib import Path
sys.path.insert(0, '${ROOT}/scripts')
import scope_utils as s
scope = json.loads(Path('${SCOPE_FILE}').read_text(encoding='utf-8'))
ok, msg = s.validate_target_url('https://${DOMAIN}', scope)
if not ok:
    print(msg, file=sys.stderr)
    sys.exit(1)
" 2>"${TMPDIR:-/tmp}/scope_err.$$"; then
    log "SCOPE: target not allowed — see stderr"
    python3 -c "import json; print(json.dumps({'ok':false,'error':'target outside pentest scope'}))"
    exit 1
  fi
fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="${SCAN_ROOT}/${DOMAIN}_${STAMP}"
mkdir -p "$WORKDIR"
if [[ -f "$SCOPE_FILE" ]]; then
  cp "$SCOPE_FILE" "${WORKDIR}/scope.json"
fi
SCAN_START_EPOCH="$(date +%s)"

log() { echo "[scan] $*" >&2; }

tool_present() { command -v "$1" >/dev/null 2>&1; }

guard_sleep() {
  REQUEST_DELAY_MS="$REQUEST_DELAY_MS" REQUESTS_PER_MINUTE="$REQUESTS_PER_MINUTE" \
    python3 "$GUARD_PY" sleep "$WORKDIR" 2>/dev/null || true
}

guard_stopped() {
  [[ -f "${WORKDIR}/.scan_stop" ]] && return 0
  python3 "$GUARD_PY" should-stop "$WORKDIR" 2>/dev/null | grep -q '^true$'
}

guard_check_httpx() {
  python3 "$GUARD_PY" analyze-httpx "$WORKDIR" >/dev/null 2>&1 || true
}

guard_probe_url() {
  local url="$1"
  guard_sleep
  python3 "$GUARD_PY" probe-url "$WORKDIR" "$url" >/dev/null 2>&1 || true
}

kill_scan_children() {
  pkill -f "${WORKDIR}" 2>/dev/null || true
}

emit_final_json() {
  local blocked_flag="false"
  local guard_json="{}"
  if [[ -f "${WORKDIR}/guard_state.json" ]]; then
    guard_json="$(cat "${WORKDIR}/guard_state.json" 2>/dev/null || echo '{}')"
    if echo "$guard_json" | grep -q '"blocked"[[:space:]]*:[[:space:]]*true'; then
      blocked_flag="true"
    fi
  fi
  export DOMAIN_VAL="$DOMAIN" WORKDIR_VAL="$WORKDIR" PROFILE_VAL="$SCAN_PROFILE"
  export WORDLIST_VAL="$WORDLIST"
  export TOOLS_USED_VAL="${TOOLS_USED[*]}" TOOLS_MISSING_VAL="${TOOLS_MISSING[*]}"
  export LIGHT_VAL="$LIGHT_RESULT" DEEP_VAL="$DEEP_RESULT"
  export BLOCKED_FLAG="$blocked_flag" GUARD_JSON="$guard_json"
  if [[ -f "${ROOT}/scripts/aggregate_vulnerabilities.py" ]]; then
    VULN_SUMMARY="$(python3 "${ROOT}/scripts/aggregate_vulnerabilities.py" "$WORKDIR" 2>/dev/null | tail -n 1 || echo '{}')"
  else
    VULN_SUMMARY='{}'
  fi
  export VULN_SUMMARY
  python3 - <<'PY'
import json, os

install = []
missing = os.environ.get("TOOLS_MISSING_VAL", "")
for pkg in ("nmap", "nuclei", "nikto"):
    if pkg in missing:
        install.append(pkg)

vulns = json.loads(os.environ.get("VULN_SUMMARY") or "{}")
guard = json.loads(os.environ.get("GUARD_JSON") or "{}")
blocked = os.environ.get("BLOCKED_FLAG") == "true" or guard.get("blocked")

out = {
    "ok": not blocked,
    "blocked": blocked,
    "domain": os.environ["DOMAIN_VAL"],
    "workdir": os.environ["WORKDIR_VAL"],
    "scan_profile": os.environ["PROFILE_VAL"],
    "wordlist": os.environ.get("WORDLIST_VAL", ""),
    "light": json.loads(os.environ.get("LIGHT_VAL") or "{}"),
    "deep": json.loads(os.environ.get("DEEP_VAL") or "{}"),
    "vulnerabilities": vulns,
    "guard": guard,
    "tester_message": guard.get("tester_message", "") if blocked else "",
    "recommendations": guard.get("recommendations", []) if blocked else [],
    "subdomains_scanned": json.loads(os.environ.get("LIGHT_VAL") or "{}").get("live_url_count", 0),
    "tools_used": [t for t in os.environ.get("TOOLS_USED_VAL", "").split() if t],
    "tools_missing": [t for t in os.environ.get("TOOLS_MISSING_VAL", "").split() if t],
    "install_packages": install,
    "install_hint": ("sudo apt install -y " + " ".join(install)) if install else "",
}
if blocked:
    out["error"] = out["tester_message"] or "Target appears to be blocking scanner IP; scan halted."
print(json.dumps(out))
PY
}

abort_if_runtime_exceeded() {
  local cap="${SCAN_MAX_RUNTIME_MINUTES:-0}"
  [[ "$cap" =~ ^[0-9]+$ ]] && (( cap > 0 )) || return 0
  local elapsed=$(( $(date +%s) - SCAN_START_EPOCH ))
  if (( elapsed >= cap * 60 )); then
    log "RUNTIME CAP: stopping after ${cap} minutes"
    touch "${WORKDIR}/.scan_stop"
    kill_scan_children
    emit_final_json
    exit 0
  fi
}

abort_if_blocked() {
  abort_if_runtime_exceeded
  if guard_stopped; then
    log "BLOCKED: stopping scan — target may be rate-limiting or blocking this IP"
    kill_scan_children
    emit_final_json
    exit 0
  fi
}

TOOLS_USED=()
TOOLS_MISSING=()
for t in subfinder httpx ffuf nmap nuclei nikto curl; do
  if tool_present "$t"; then
    TOOLS_USED+=("$t")
  else
    TOOLS_MISSING+=("$t")
  fi
done

run_sqli_checks() {
  [[ "$SQLI_SCAN" == "1" ]] || return 0
  if [[ ! -f "${ROOT}/scripts/scan_sqli.py" ]]; then
    log "scan_sqli.py missing — skip SQLi phase"
    return 0
  fi
  if [[ -f "${WORKDIR}/sqli_summary.json" ]]; then
    return 0
  fi
  if [[ ! -s "${WORKDIR}/live_urls.txt" ]]; then
    echo "https://${DOMAIN}" >"${WORKDIR}/live_urls.txt"
  fi
  abort_if_blocked
  log "SQL injection checks (nuclei sqli + safe probes, max $SQLI_MAX_URLS URLs)"
  export SQLI_MAX_URLS SQLI_TIMEOUT REQUEST_DELAY_MS REQUESTS_PER_MINUTE WORKDIR
  python3 "${ROOT}/scripts/scan_sqli.py" "$WORKDIR" \
    >"${WORKDIR}/sqli.stdout" 2>"${WORKDIR}/sqli.err" || true
  abort_if_blocked
}

run_light() {
  log "light scan: $DOMAIN"
  guard_probe_url "https://${DOMAIN}"
  abort_if_blocked
  local subs_file="${WORKDIR}/subdomains.txt"
  local hosts_file="${WORKDIR}/hosts.txt"
  local live_json="${WORKDIR}/live.json"
  local ffuf_json="${WORKDIR}/ffuf.json"
  local headers_raw="${WORKDIR}/headers_raw.txt"

  touch "$subs_file"
  if tool_present subfinder; then
    guard_sleep
    subfinder -d "$DOMAIN" -silent -o "$subs_file" 2>"${WORKDIR}/subfinder.err" || true
    abort_if_blocked
  fi

  {
    echo "$DOMAIN"
    [[ -s "$subs_file" ]] && cat "$subs_file"
  } | awk 'NF' | sort -u >"$hosts_file"

  if [[ -f "${WORKDIR}/scope.json" ]]; then
    log "filtering hosts by pentest scope"
    python3 "${ROOT}/scripts/scope_utils.py" filter-workdir "${WORKDIR}" 2>"${WORKDIR}/scope_filter.err" || true
  fi

  local live_url="https://${DOMAIN}"
  if tool_present httpx && [[ -s "$hosts_file" ]]; then
    guard_sleep
    local httpx_rl=$(( (REQUESTS_PER_MINUTE + 59) / 60 ))
    [[ "$httpx_rl" -lt 1 ]] && httpx_rl=1
    httpx -l "$hosts_file" -silent -status-code -title -tech-detect -follow-redirects -json \
      -rl "$httpx_rl" -o "$live_json" 2>"${WORKDIR}/httpx.err" || true
    guard_check_httpx
    abort_if_blocked
    if [[ -s "$live_json" ]]; then
      jq -r '(.url // .final_url // empty), (.input // empty) | select(length>0)' "$live_json" 2>/dev/null \
        | while read -r u; do
            [[ "$u" == http* ]] && echo "$u" || echo "https://$u"
          done | sort -u >"${WORKDIR}/live_urls.txt" || true
    fi
    local first
    first="$(head -n 1 "${WORKDIR}/live_urls.txt" 2>/dev/null || true)"
    [[ -n "$first" ]] && live_url="$first"
  fi

  local ffuf_findings=0
  if [[ "$FFUF_PER_HOST" != "1" ]] && tool_present ffuf && [[ -f "$WORDLIST" ]]; then
    guard_sleep
    ffuf -w "$WORDLIST" -u "${live_url%/}/FUZZ" -t "$THREADS" -ac -s -maxtime "$FFUF_MAXTIME" \
      -mc "$FFUF_MATCH_CODES" -o "$ffuf_json" -of json 2>"${WORKDIR}/ffuf.err" || true
    ffuf_findings="$(jq '.results | length' "$ffuf_json" 2>/dev/null || echo 0)"
  fi

  local header_issues=()
  guard_sleep
  curl -sSI "$live_url" -m 25 2>/dev/null | tee "$headers_raw" >/dev/null || true
  abort_if_blocked
  has_header() { grep -qi "^$1:" "$headers_raw" 2>/dev/null; }
  has_header "x-frame-options" || header_issues+=("missing_x_frame_options")
  has_header "content-security-policy" || header_issues+=("missing_csp")
  has_header "strict-transport-security" || header_issues+=("missing_hsts")

  local sub_count=0
  [[ -s "$subs_file" ]] && sub_count="$(wc -l <"$subs_file" | tr -d ' ')"

  echo "$live_url" >>"${WORKDIR}/live_urls.txt" 2>/dev/null || true
  sort -u -o "${WORKDIR}/live_urls.txt" "${WORKDIR}/live_urls.txt" 2>/dev/null || true

  if [[ -f "${ROOT}/scripts/analyze_web_security.py" ]]; then
    python3 "${ROOT}/scripts/analyze_web_security.py" "$DOMAIN" "$WORKDIR" "$live_url" \
      >"${WORKDIR}/web_security.stdout" 2>"${WORKDIR}/web_security.err" || true
  fi

  if [[ "$SCAN_ALL_SUBDOMAINS" == "1" && -f "${ROOT}/scripts/scan_subdomains.py" ]]; then
    abort_if_blocked
    log "per-subdomain scans (max $MAX_SUBDOMAIN_SCANS hosts)"
    export APEX_DOMAIN="$DOMAIN" WORDLIST THREADS FFUF_MAXTIME FFUF_PER_HOST
    export MAX_SUBDOMAIN_SCANS PER_HOST_NUCLEI_TIMEOUT NUCLEI_PER_HOST NUCLEI_TAGS NUCLEI_SEVERITY
    export REQUEST_DELAY_MS REQUESTS_PER_MINUTE BLOCK_CONSECUTIVE_THRESHOLD WORKDIR
    python3 "${ROOT}/scripts/scan_subdomains.py" "$WORKDIR" \
      >"${WORKDIR}/hosts_scan.stdout" 2>"${WORKDIR}/hosts_scan.err" || true
    abort_if_blocked
    if [[ -f "${WORKDIR}/hosts_scan.json" ]]; then
      ffuf_findings="$(python3 -c "import json;print(sum(h.get('findings_count',0) for h in json.load(open('${WORKDIR}/hosts_scan.json')).get('hosts',[])))" 2>/dev/null || echo "$ffuf_findings")"
    fi
  fi

  run_sqli_checks

  python3 - "$DOMAIN" "$WORKDIR" "$sub_count" "$ffuf_findings" "${header_issues[*]}" "$live_url" <<'PY'
import json, sys
from pathlib import Path

domain, workdir, sub_count, ffuf_findings, header_issues, live_url = sys.argv[1:7]
wd = Path(workdir)
header_issues = [x for x in header_issues.split() if x]

def read_lines(name):
    p = wd / name
    return [ln.strip() for ln in p.read_text().splitlines() if ln.strip()] if p.exists() else []

live = []
if (wd / "live.json").exists():
    for line in (wd / "live.json").read_text().splitlines():
        line = line.strip()
        if line:
            try:
                live.append(json.loads(line))
            except json.JSONDecodeError:
                pass

ffuf = []
if (wd / "ffuf.json").exists():
    try:
        ffuf = json.loads((wd / "ffuf.json").read_text()).get("results", [])[:25]
    except json.JSONDecodeError:
        pass

out = {
    "path": "light",
    "domain": domain,
    "live_url": live_url,
    "subdomain_count": int(sub_count or 0),
    "subdomains_sample": read_lines("subdomains.txt")[:15],
    "live_hosts": live[:50],
    "live_url_count": len(live),
    "ffuf_findings": int(ffuf_findings or 0),
    "ffuf_sample": ffuf,
    "header_issues": header_issues,
}
sqli_findings = 0
sqli_sample = []
sqli_path = wd / "sqli_summary.json"
if sqli_path.exists():
    try:
        sqli_data = json.loads(sqli_path.read_text())
        sqli_findings = int(sqli_data.get("findings") or 0)
        sqli_sample = sqli_data.get("sample") or []
    except json.JSONDecodeError:
        pass
out["sqli_findings"] = sqli_findings
out["sqli_sample"] = sqli_sample[:10]
(wd / "light.json").write_text(json.dumps(out))
print(json.dumps(out))
PY
}

run_deep() {
  log "deep scan: $DOMAIN"
  abort_if_blocked
  run_sqli_checks
  local nmap_out="${WORKDIR}/nmap.xml"
  local nuclei_out="${WORKDIR}/nuclei.jsonl"
  local deep_errors=()
  local nmap_findings=0
  local nmap_ports_sample='[]'
  local nuclei_findings=0
  local nuclei_sample='[]'

  if tool_present nmap; then
    guard_sleep
    log "nmap apex ports ($NMAP_APEX_PORTS) — avoids noisy Cloudflare top-100"
    nmap -Pn -sV -T4 -p "$NMAP_APEX_PORTS" "$DOMAIN" -oX "$nmap_out" \
      >"${WORKDIR}/nmap.stdout" 2>"${WORKDIR}/nmap.err" || true
    python3 - "$nmap_out" <<'PY' >"${WORKDIR}/nmap_summary.json" 2>/dev/null || echo '{"open_count":0,"ports":[]}' >"${WORKDIR}/nmap_summary.json"
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path
path = Path(sys.argv[1])
ports = []
if path.exists() and path.stat().st_size > 0:
    try:
        root = ET.parse(path).getroot()
        for host in root.findall("host"):
            for port in host.findall(".//port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                service = port.find("service")
                ports.append({
                    "port": port.get("portid"),
                    "protocol": port.get("protocol"),
                    "service": service.get("name") if service is not None else "",
                    "product": service.get("product") if service is not None else "",
                })
    except Exception:
        pass
print(json.dumps({"open_count": len(ports), "ports": ports[:30]}))
PY
    nmap_findings="$(jq -r '.open_count // 0' "${WORKDIR}/nmap_summary.json" 2>/dev/null || echo 0)"
    nmap_ports_sample="$(jq -c '.ports // []' "${WORKDIR}/nmap_summary.json" 2>/dev/null || echo '[]')"
  else
    deep_errors+=("nmap_not_installed")
  fi

  if tool_present nmap; then
    log "nmap NSE scripts ($NMAP_SCRIPTS)"
    timeout 120 nmap -Pn -sV -p 80,443,8080,8443 --script "$NMAP_SCRIPTS" "$DOMAIN" \
      -oX "${WORKDIR}/nmap_scripts.xml" >"${WORKDIR}/nmap_scripts.stdout" 2>"${WORKDIR}/nmap_scripts.err" || true
    python3 - "${WORKDIR}/nmap_scripts.xml" <<'PY' >"${WORKDIR}/nmap_scripts.json" 2>/dev/null || true
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path
findings = []
path = Path(sys.argv[1])
if path.exists() and path.stat().st_size > 0:
    try:
        root = ET.parse(path).getroot()
        for host in root.findall("host"):
            for port in host.findall(".//port"):
                for script in port.findall("script"):
                    sid = script.get("id", "nmap-script")
                    out = script.get("output", "").strip()
                    if not out or len(out) < 4:
                        continue
                    sev = "info"
                    low = out.lower()
                    if any(x in low for x in ("vuln", "cve", "weak", "expired", "unsupported")):
                        sev = "medium"
                    if any(x in low for x in ("critical", "sslv3", "rc4", "md5")):
                        sev = "high"
                    findings.append({
                        "severity": sev,
                        "title": f"nmap {sid}: {out[:120]}",
                        "type": "nmap_script",
                        "code": sid,
                        "source": "nmap",
                        "description": out[:500],
                    })
    except Exception:
        pass
print(json.dumps({"findings": findings[:40]}))
PY
  fi

  if tool_present nikto; then
    log "nikto scan"
    local nikto_ok=0
    for nikto_url in "https://${DOMAIN}" "http://${DOMAIN}"; do
      if timeout "$NIKTO_TIMEOUT" nikto -h "$nikto_url" -o "${WORKDIR}/nikto.json" -Format json \
        -nocheck -nointeractive >"${WORKDIR}/nikto.stdout" 2>"${WORKDIR}/nikto.err"; then
        if [[ -s "${WORKDIR}/nikto.json" ]]; then
          nikto_ok=1
          break
        fi
      fi
    done
    if [[ "$nikto_ok" -ne 1 ]]; then
      deep_errors+=("nikto_no_results")
    fi
  else
    deep_errors+=("nikto_not_installed")
  fi

  if tool_present nuclei; then
    log "nuclei ($NUCLEI_TAGS) severity=$NUCLEI_SEVERITY"
    : >"$nuclei_out"
    local url_list="${WORKDIR}/live_urls.txt"
    if [[ -s "$url_list" ]]; then
      timeout "$NUCLEI_TIMEOUT" nuclei -l "$url_list" -tags "$NUCLEI_TAGS" \
        -severity "$NUCLEI_SEVERITY" -silent -jsonl -timeout 8 -retries 1 \
        -o "$nuclei_out" 2>>"${WORKDIR}/nuclei.err" || true
    fi
    for url in "https://${DOMAIN}" "http://${DOMAIN}"; do
      timeout 60 nuclei -u "$url" -tags "$NUCLEI_TAGS" -severity "$NUCLEI_SEVERITY" \
        -silent -jsonl -timeout 8 -retries 1 -o "$nuclei_out" 2>>"${WORKDIR}/nuclei.err" || true
    done
    if [[ -s "$nuclei_out" ]]; then
      nuclei_findings="$(wc -l <"$nuclei_out" | tr -d ' ')"
      nuclei_sample="$(python3 - <<'PY' "$nuclei_out"
import json, sys
from pathlib import Path
items = []
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.strip():
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            pass
print(json.dumps(items[:20]))
PY
)"
    fi
  else
    deep_errors+=("nuclei_not_installed")
  fi

  python3 - "$DOMAIN" "$WORKDIR" "$nuclei_findings" "${deep_errors[*]}" <<'PY'
import json, sys
from pathlib import Path

domain, workdir, nuclei_findings, deep_errors = sys.argv[1:5]
wd = Path(workdir)
errors = [x for x in deep_errors.split() if x]

nmap_ports = []
nmap_findings = 0
summary = wd / "nmap_summary.json"
if summary.exists():
    try:
        summary_data = json.loads(summary.read_text())
        nmap_ports = summary_data.get("ports", [])
        nmap_findings = int(summary_data.get("open_count", len(nmap_ports)))
    except json.JSONDecodeError:
        pass

nuclei_items = []
nuclei_path = wd / "nuclei.jsonl"
if nuclei_path.exists():
    for line in nuclei_path.read_text().splitlines():
        if line.strip():
            try:
                nuclei_items.append(json.loads(line))
            except json.JSONDecodeError:
                pass

out = {
    "path": "deep",
    "domain": domain,
    "nmap_findings": nmap_findings,
    "nmap_ports_sample": nmap_ports[:30],
    "nuclei_findings": int(nuclei_findings or 0),
    "nuclei_sample": nuclei_items[:20],
    "errors": errors,
}
(wd / "deep.json").write_text(json.dumps(out))
print(json.dumps(out))
PY
}

LIGHT_RESULT='{}'
DEEP_RESULT='{}'

if [[ "$SCAN_PROFILE" == "light" || "$SCAN_PROFILE" == "both" ]]; then
  LIGHT_RESULT="$(run_light | tail -n 1)"
  abort_if_blocked
fi

if [[ "$SCAN_PROFILE" == "deep" || "$SCAN_PROFILE" == "both" ]]; then
  DEEP_RESULT="$(run_deep | tail -n 1)"
  abort_if_blocked
fi

emit_final_json
