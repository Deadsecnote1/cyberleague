#!/usr/bin/env python3
"""SQL injection checks: nuclei sqli templates + safe error-based probes on parameterized URLs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "rate_limit_guard.py"

# Conservative signatures — possible DB error reflection (verify manually).
SQL_ERROR_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"sql syntax",
        r"mysql_",
        r"sqlite",
        r"postgresql",
        r"ora-\d{5}",
        r"sql server",
        r"unclosed quotation",
        r"quoted string not properly terminated",
        r"warning.*\Wmysqli?",
        r"pg_query",
        r"odbc sql",
    )
]

PARAM_HINTS = re.compile(
    r"^(id|page|cat|category|item|product|user|uid|pid|q|query|search|sort|order|view|file|name|type)$",
    re.I,
)


def log(msg: str) -> None:
    print(f"[sqli] {msg}", file=sys.stderr)


def guard_sleep(workdir: Path) -> None:
    if not GUARD.exists():
        return
    subprocess.run(
        ["python3", str(GUARD), "sleep", str(workdir)],
        capture_output=True,
        timeout=20,
        check=False,
    )


def guard_probe(workdir: Path, url: str) -> None:
    if not GUARD.exists():
        return
    subprocess.run(
        ["python3", str(GUARD), "probe-url", str(workdir), url],
        capture_output=True,
        timeout=30,
        check=False,
    )


def read_live_urls(workdir: Path) -> list[str]:
    urls: list[str] = []
    live_list = workdir / "live_urls.txt"
    if live_list.exists():
        urls.extend(ln.strip() for ln in live_list.read_text().splitlines() if ln.strip())
    live_json = workdir / "live.json"
    if live_json.exists():
        for line in live_json.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            u = row.get("url") or row.get("final_url")
            if u:
                urls.append(str(u).strip())
    # Prefer URLs with query strings, then any live URL
    seen: set[str] = set()
    with_params: list[str] = []
    other: list[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        if urlparse(u).query:
            with_params.append(u)
        else:
            other.append(u)
    return with_params + other


def inject_payload(url: str, payload: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        # Add a probe param if none exist (common on vuln labs)
        qs = urlencode({"id": payload})
        return urlunparse(parsed._replace(query=qs))
    pairs = parse_qs(parsed.query, keep_blank_values=True)
    new_pairs: dict[str, list[str]] = {}
    touched = False
    for key, values in pairs.items():
        if not touched and PARAM_HINTS.match(key):
            new_pairs[key] = [payload]
            touched = True
        else:
            new_pairs[key] = values
    if not touched and pairs:
        first_key = next(iter(pairs))
        new_pairs[first_key] = [payload]
    query = urlencode(new_pairs, doseq=True)
    return urlunparse(parsed._replace(query=query))


def probe_url(url: str, workdir: Path, timeout: int = 12) -> list[dict]:
    findings: list[dict] = []
    host = urlparse(url).netloc.split(":")[0].lower()
    for payload in ("'", "''"):
        test_url = inject_payload(url, payload)
        guard_sleep(workdir)
        guard_probe(workdir, test_url)
        try:
            proc = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "-m",
                    str(timeout),
                    "-A",
                    "CyberLeague-SQLiProbe/1.0",
                    "--max-redirs",
                    "3",
                    test_url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            continue
        body = (proc.stdout or "")[:8000]
        for pat in SQL_ERROR_PATTERNS:
            if pat.search(body):
                findings.append(
                    {
                        "severity": "high",
                        "title": "Possible SQL error disclosed in response",
                        "type": "sqli",
                        "category": "injection",
                        "code": "sqli_error_disclosure",
                        "source": "sqli_probe",
                        "host": host,
                        "matched_at": test_url,
                        "description": f"Response matched pattern `{pat.pattern}` after payload {payload!r}.",
                        "recommendation": "Validate manually with sqlmap/Burp; fix parameterized queries / use prepared statements.",
                    }
                )
                break
        if findings:
            break
    return findings


def run_nuclei_sqli(urls: list[str], workdir: Path, timeout: int) -> list[dict]:
    if not urls:
        return []
    nuclei = "nuclei"
    if subprocess.run(["which", nuclei], capture_output=True).returncode != 0:
        log("nuclei not installed — using probe-only SQLi checks")
        return []

    url_file = workdir / "sqli_targets.txt"
    url_file.write_text("\n".join(urls) + "\n", encoding="utf-8")
    out_path = workdir / "sqli.jsonl"
    tags = os.environ.get("SQLI_NUCLEI_TAGS", "sqli,sqli-error-based,sqli-time-based")
    severity = os.environ.get("SQLI_NUCLEI_SEVERITY", "medium,high,critical")
    guard_sleep(workdir)
    cmd = [
        "timeout",
        str(timeout),
        nuclei,
        "-l",
        str(url_file),
        "-tags",
        tags,
        "-severity",
        severity,
        "-silent",
        "-jsonl",
        "-timeout",
        "10",
        "-retries",
        "1",
        "-rate-limit",
        os.environ.get("SQLI_NUCLEI_RATE", "15"),
        "-o",
        str(out_path),
    ]
    log(f"nuclei SQLi templates on {len(urls)} URL(s)")
    subprocess.run(cmd, capture_output=True, text=True, check=False)

    findings: list[dict] = []
    if not out_path.exists():
        return findings
    for line in out_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = item.get("info") or {}
        host = urlparse(str(item.get("host") or item.get("matched-at") or "")).netloc
        findings.append(
            {
                "severity": (info.get("severity") or "high").lower(),
                "title": info.get("name") or item.get("template-id") or "SQL injection (nuclei)",
                "type": "sqli",
                "category": "injection",
                "code": item.get("template-id") or "nuclei_sqli",
                "source": "nuclei_sqli",
                "host": host.split(":")[0] if host else "",
                "matched_at": item.get("matched-at") or item.get("host") or "",
                "description": (info.get("description") or "")[:400],
                "recommendation": "Confirm exploitability; remediate with parameterized queries and input validation.",
            }
        )
    return findings


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scan_sqli.py <workdir>", file=sys.stderr)
        return 1

    workdir = Path(sys.argv[1])
    max_urls = int(os.environ.get("SQLI_MAX_URLS", "12"))
    timeout = int(os.environ.get("SQLI_TIMEOUT", "120"))
    use_nuclei = os.environ.get("SQLI_USE_NUCLEI", "1") == "1"
    use_probe = os.environ.get("SQLI_USE_PROBE", "1") == "1"

    urls = read_live_urls(workdir)[:max_urls]
    if not urls:
        log("no live URLs — skipping SQLi phase")
        summary = {"ok": True, "skipped": True, "reason": "no_urls", "findings": 0}
        (workdir / "sqli_summary.json").write_text(json.dumps(summary, indent=2))
        return 0

    all_findings: list[dict] = []

    if use_nuclei:
        all_findings.extend(run_nuclei_sqli(urls, workdir, timeout))

    if use_probe:
        for url in urls[: min(6, len(urls))]:
            if any(f.get("matched_at", "").startswith(url.split("?")[0]) for f in all_findings):
                continue
            all_findings.extend(probe_url(url, workdir))

    # Dedupe
    seen: set[str] = set()
    unique: list[dict] = []
    for f in all_findings:
        key = "|".join([f.get("host", ""), f.get("code", ""), f.get("title", ""), f.get("matched_at", "")])
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)

    if unique:
        out = workdir / "sqli.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for f in unique:
                fh.write(json.dumps(f) + "\n")

    summary = {
        "ok": True,
        "urls_tested": len(urls),
        "findings": len(unique),
        "methods": {
            "nuclei": use_nuclei,
            "probe": use_probe,
        },
        "sample": unique[:10],
    }
    (workdir / "sqli_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
