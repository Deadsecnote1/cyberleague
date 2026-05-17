#!/usr/bin/env python3
"""Run security checks against every discovered subdomain / live URL."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "rate_limit_guard.py"
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import scope_utils as scope_mod  # noqa: E402


def log(msg: str) -> None:
    print(f"[subdomains] {msg}", file=sys.stderr)


def sanitize_host(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:120]


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]


def load_httpx_hosts(workdir: Path) -> list[dict]:
    hosts: dict[str, dict] = {}
    live_json = workdir / "live.json"
    if live_json.exists():
        for line in live_json.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = row.get("url") or row.get("final_url")
            if not url and row.get("input"):
                scheme = "https" if str(row.get("scheme", "https")) == "https" else "http"
                url = f"{scheme}://{row['input']}"
            if not url:
                continue
            host = urlparse(url).netloc.split(":")[0].lower()
            if not host:
                continue
            hosts[host] = {
                "host": host,
                "url": url,
                "status_code": row.get("status_code") or row.get("status-code"),
                "title": row.get("title") or "",
                "technologies": row.get("tech") or row.get("technologies") or [],
                "live": True,
            }

    for sub in read_lines(workdir / "subdomains.txt"):
        sub = sub.lower().strip()
        if sub and sub not in hosts:
            hosts[sub] = {
                "host": sub,
                "url": f"https://{sub}",
                "status_code": None,
                "title": "",
                "technologies": [],
                "live": False,
            }

    apex = os.environ.get("APEX_DOMAIN", "").lower()
    if apex and apex not in hosts:
        hosts[apex] = {
            "host": apex,
            "url": f"https://{apex}",
            "status_code": None,
            "title": "",
            "technologies": [],
            "live": False,
        }

    return list(hosts.values())


def guard_stopped(workdir: Path) -> bool:
    if (workdir / ".scan_stop").exists():
        return True
    if not GUARD.exists():
        return False
    rc, out, _ = run_cmd_simple(["python3", str(GUARD), "should-stop", str(workdir)], timeout=10)
    return out.strip() == "true"


def guard_sleep(workdir: Path) -> None:
    if not GUARD.exists():
        return
    run_cmd_simple(["python3", str(GUARD), "sleep", str(workdir)], timeout=15)


def run_cmd_simple(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def run_cmd(cmd: list[str], timeout: int = 90) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def scan_host(
    entry: dict,
    host_dir: Path,
    *,
    wordlist: Path,
    ffuf_maxtime: int,
    ffuf_threads: int,
    run_ffuf: bool,
    run_security: bool,
    run_nuclei: bool,
    nuclei_tags: str,
    nuclei_severity: str,
    nuclei_timeout: int,
) -> dict:
    host = entry["host"]
    url = entry["url"]
    findings: list[dict] = []
    host_dir.mkdir(parents=True, exist_ok=True)

    if run_security:
        script = ROOT / "scripts" / "analyze_web_security.py"
        if script.exists():
            rc, out, err = run_cmd(
                ["python3", str(script), host, str(host_dir), url], timeout=45
            )
            sec_path = host_dir / "web_security.json"
            if sec_path.exists():
                try:
                    findings.extend(json.loads(sec_path.read_text()).get("findings", []))
                except json.JSONDecodeError:
                    pass
            for f in findings:
                f["host"] = host

    if run_ffuf and wordlist.exists() and entry.get("live"):
        ffuf_out = host_dir / "ffuf.json"
        cmd = [
            "ffuf",
            "-w",
            str(wordlist),
            "-u",
            f"{url.rstrip('/')}/FUZZ",
            "-t",
            str(ffuf_threads),
            "-ac",
            "-s",
            "-maxtime",
            str(ffuf_maxtime),
            "-mc",
            "200,204,301,302,307,401,403",
            "-o",
            str(ffuf_out),
            "-of",
            "json",
        ]
        run_cmd(cmd, timeout=ffuf_maxtime + 30)
        if ffuf_out.exists():
            try:
                for hit in json.loads(ffuf_out.read_text()).get("results", [])[:15]:
                    status = hit.get("status")
                    hit_url = hit.get("url", "")
                    findings.append(
                        {
                            "severity": "low" if status in (200, 401, 403) else "info",
                            "title": f"Path [{status}]: {hit_url}",
                            "type": "exposed_path",
                            "code": "ffuf_path",
                            "source": "ffuf",
                            "host": host,
                            "matched_at": hit_url,
                        }
                    )
            except json.JSONDecodeError:
                pass

    if run_nuclei and entry.get("live"):
        nuclei_out = host_dir / "nuclei.jsonl"
        cmd = [
            "nuclei",
            "-u",
            url,
            "-tags",
            nuclei_tags,
            "-severity",
            nuclei_severity,
            "-silent",
            "-jsonl",
            "-timeout",
            "8",
            "-retries",
            "1",
            "-o",
            str(nuclei_out),
        ]
        run_cmd(cmd, timeout=nuclei_timeout)
        if nuclei_out.exists():
            for line in nuclei_out.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    info = item.get("info") or {}
                    findings.append(
                        {
                            "severity": (info.get("severity") or "unknown").lower(),
                            "title": info.get("name") or item.get("template-id", "nuclei"),
                            "type": "nuclei",
                            "code": item.get("template-id", "nuclei"),
                            "source": "nuclei",
                            "host": host,
                            "matched_at": item.get("matched-at") or url,
                            "description": (info.get("description") or "")[:300],
                        }
                    )
                except json.JSONDecodeError:
                    pass

    return {
        **entry,
        "findings_count": len(findings),
        "findings": findings,
        "artifact_dir": str(host_dir),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scan_subdomains.py <workdir>", file=sys.stderr)
        return 1

    workdir = Path(sys.argv[1])
    os.environ.setdefault("APEX_DOMAIN", workdir.name.split("_")[0])

    max_hosts = int(os.environ.get("MAX_SUBDOMAIN_SCANS", "25"))
    wordlist = Path(os.environ.get("WORDLIST", ROOT / "wordlists/ffuf-quick.txt"))
    ffuf_maxtime = int(os.environ.get("FFUF_MAXTIME", "60"))
    ffuf_threads = int(os.environ.get("THREADS", "30"))
    run_ffuf = os.environ.get("FFUF_PER_HOST", "1") == "1"
    run_security = os.environ.get("SECURITY_PER_HOST", "1") == "1"
    run_nuclei = os.environ.get("NUCLEI_PER_HOST", "1") == "1"
    nuclei_tags = os.environ.get(
        "NUCLEI_TAGS", "cve,vuln,misconfig,exposure,tech,panel,default-logins,sqli"
    )
    nuclei_severity = os.environ.get("NUCLEI_SEVERITY", "medium,high,critical")
    nuclei_timeout = int(os.environ.get("PER_HOST_NUCLEI_TIMEOUT", "60"))

    entries = load_httpx_hosts(workdir)
    scope_path = workdir / "scope.json"
    if scope_path.exists():
        try:
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
            before = len(entries)
            entries = [e for e in entries if scope_mod.is_host_in_scope(e["host"], scope)]
            dropped = before - len(entries)
            if dropped:
                log(f"scope: excluded {dropped} host(s) outside pentest scope")
        except (json.JSONDecodeError, OSError) as exc:
            log(f"scope: could not apply filter ({exc})")
    # Prefer live hosts first
    entries.sort(key=lambda e: (not e.get("live"), e["host"]))
    if len(entries) > max_hosts:
        log(f"capping subdomain scans at {max_hosts} of {len(entries)} hosts")
        entries = entries[:max_hosts]

    hosts_root = workdir / "hosts"
    hosts_root.mkdir(exist_ok=True)
    results: list[dict] = []

    for entry in entries:
        if guard_stopped(workdir):
            log("BLOCKED: stopping per-host scans (IP/rate limit)")
            break
        guard_sleep(workdir)
        host_dir = hosts_root / sanitize_host(entry["host"])
        log(f"scanning {entry['host']} ({entry['url']})")
        if GUARD.exists():
            run_cmd_simple(
                ["python3", str(GUARD), "probe-url", str(workdir), entry["url"]], timeout=30
            )
            if guard_stopped(workdir):
                log("BLOCKED after probe — halting subdomain scans")
                break
        results.append(
            scan_host(
                entry,
                host_dir,
                wordlist=wordlist,
                ffuf_maxtime=ffuf_maxtime,
                ffuf_threads=ffuf_threads,
                run_ffuf=run_ffuf,
                run_security=run_security,
                run_nuclei=run_nuclei,
                nuclei_tags=nuclei_tags,
                nuclei_severity=nuclei_severity,
                nuclei_timeout=nuclei_timeout,
            )
        )

    # Merge all per-host nuclei into workdir nuclei.jsonl for legacy aggregate
    nuclei_merged = workdir / "nuclei.jsonl"
    with nuclei_merged.open("w", encoding="utf-8") as out:
        for host_dir in hosts_root.iterdir():
            nf = host_dir / "nuclei.jsonl"
            if nf.exists():
                out.write(nf.read_text())

    blocked = guard_stopped(workdir)
    out = {
        "hosts_scanned": len(results),
        "hosts_live": sum(1 for r in results if r.get("live")),
        "hosts": results,
        "blocked": blocked,
    }
    (workdir / "hosts_scan.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"ok": True, "hosts_scanned": len(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
