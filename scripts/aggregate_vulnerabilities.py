#!/usr/bin/env python3
"""Merge tool outputs into a unified, categorized vulnerability list."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def nuclei_to_vuln(item: dict, host: str = "") -> dict:
    info = item.get("info") or {}
    return {
        "severity": (info.get("severity") or "unknown").lower(),
        "title": info.get("name") or item.get("template-id") or "nuclei finding",
        "type": "nuclei",
        "category": "vulnerability_template",
        "code": item.get("template-id") or "nuclei",
        "source": "nuclei",
        "host": host or urlparse_host(item.get("host") or item.get("matched-at") or ""),
        "matched_at": item.get("matched-at") or item.get("host") or "",
        "description": (info.get("description") or "")[:400],
        "recommendation": "Verify manually; check CVE/template reference and business impact.",
    }


def urlparse_host(value: str) -> str:
    if not value:
        return ""
    if "://" in value:
        from urllib.parse import urlparse

        return urlparse(value).netloc.split(":")[0].lower()
    return value.split("/")[0].split(":")[0].lower()


def ffuf_to_vuln(result: dict, base_url: str, host: str = "") -> dict:
    status = result.get("status")
    url = result.get("url") or ""
    sev = "low" if status in (200, 204, 401, 403) else "info"
    return {
        "severity": sev,
        "title": f"Discovered path [{status}]: {url}",
        "type": "exposed_path",
        "category": "attack_surface",
        "code": "ffuf_path",
        "source": "ffuf",
        "host": host or urlparse_host(base_url),
        "matched_at": url,
        "description": f"Discovered via directory brute-force. Base: {base_url}",
        "recommendation": "Confirm if path exposes admin, backup, or sensitive functionality.",
    }


def enrich_finding(f: dict) -> dict:
    f = dict(f)
    f.setdefault("category", f.get("type", "general"))
    f.setdefault("host", "")
    rec_map = {
        "missing_hsts": "Enable HSTS on all HTTPS responses.",
        "missing_csp": "Define a strict Content-Security-Policy.",
        "missing_x_frame_options": "Set X-Frame-Options or frame-ancestors in CSP.",
        "missing_x_content_type_options": "Set X-Content-Type-Options: nosniff.",
        "insecure_cookie": "Add Secure, HttpOnly, and SameSite on session cookies.",
        "weak_tls_protocol": "Disable TLS 1.0/1.1; use modern cipher suites.",
        "cert_expired": "Renew TLS certificate immediately.",
    }
    f.setdefault(
        "recommendation",
        rec_map.get(f.get("code", ""), "Review and validate impact on this host."),
    )
    return f


def aggregate(workdir: Path) -> dict:
    vulns: list[dict] = []

    hosts_scan = workdir / "hosts_scan.json"
    if hosts_scan.exists():
        data = json.loads(hosts_scan.read_text())
        for host_row in data.get("hosts", []):
            host = host_row.get("host", "")
            for f in host_row.get("findings", []):
                item = enrich_finding(f)
                item["host"] = item.get("host") or host
                vulns.append(item)

    web_sec = workdir / "web_security.json"
    if web_sec.exists():
        for f in json.loads(web_sec.read_text()).get("findings", []):
            item = enrich_finding(f)
            if not item.get("host"):
                item["host"] = workdir.name.split("_")[0]
            vulns.append(item)

    sqli_path = workdir / "sqli.jsonl"
    if sqli_path.exists():
        for line in sqli_path.read_text().splitlines():
            if line.strip():
                try:
                    f = json.loads(line)
                    item = enrich_finding(f)
                    item["category"] = item.get("category") or "injection"
                    item["type"] = "sqli"
                    if not item.get("host"):
                        item["host"] = urlparse_host(item.get("matched_at", ""))
                    vulns.append(item)
                except json.JSONDecodeError:
                    pass

    nuclei_path = workdir / "nuclei.jsonl"
    if nuclei_path.exists():
        for line in nuclei_path.read_text().splitlines():
            if line.strip():
                try:
                    raw = json.loads(line)
                    vulns.append(nuclei_to_vuln(raw, urlparse_host(raw.get("host", ""))))
                except json.JSONDecodeError:
                    pass

    for nikto_path in (workdir / "nikto.json", workdir / "nikto.json.json"):
        if not nikto_path.exists() or nikto_path.stat().st_size == 0:
            continue
        try:
            data = json.loads(nikto_path.read_text())
            for entry in data.get("vulnerabilities", data.get("host", {}).get("vulnerabilities", [])):
                if isinstance(entry, dict):
                    vulns.append(
                        enrich_finding(
                            {
                                "severity": (entry.get("severity") or "info").lower(),
                                "title": entry.get("msg") or entry.get("description") or "nikto finding",
                                "type": "nikto",
                                "category": "web_server",
                                "code": "nikto",
                                "source": "nikto",
                                "host": urlparse_host(entry.get("url") or ""),
                                "matched_at": entry.get("url") or "",
                                "description": entry.get("msg") or "",
                            }
                        )
                    )
            break
        except json.JSONDecodeError:
            continue

    nmap_vuln = workdir / "nmap_scripts.json"
    if nmap_vuln.exists() and nmap_vuln.stat().st_size > 0:
        try:
            for f in json.loads(nmap_vuln.read_text()).get("findings", []):
                item = enrich_finding(f)
                item.setdefault("host", workdir.name.split("_")[0])
                item["category"] = "network"
                vulns.append(item)
        except json.JSONDecodeError:
            pass

    light_path = workdir / "light.json"
    if light_path.exists():
        light = json.loads(light_path.read_text())
        base_url = light.get("live_url", "")
        apex = light.get("domain", "")
        for hit in light.get("ffuf_sample", []):
            vulns.append(ffuf_to_vuln(hit, base_url, apex))
        for hit in light.get("ffuf_by_host", []):
            vulns.append(
                ffuf_to_vuln(hit.get("result", hit), hit.get("url", base_url), hit.get("host", apex))
            )

    # Deduplicate
    seen: set[str] = set()
    unique: list[dict] = []
    for v in vulns:
        key = "|".join(
            [
                v.get("host", ""),
                v.get("code", ""),
                v.get("title", ""),
                v.get("matched_at", ""),
            ]
        )
        if key not in seen:
            seen.add(key)
            unique.append(v)

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "unknown": 5}
    unique.sort(key=lambda v: (order.get(v.get("severity", "unknown"), 9), v.get("host", "")))

    by_severity: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    by_host: dict[str, list] = defaultdict(list)
    for v in unique:
        by_severity[v.get("severity", "unknown")] += 1
        by_category[v.get("category", v.get("type", "general"))] += 1
        by_host[v.get("host") or "unknown"].append(v)

    # Actionable summary
    actions: list[str] = []
    if by_severity.get("critical") or by_severity.get("high"):
        actions.append("Prioritize critical/high nuclei and TLS findings first.")
    if by_category.get("security_header", 0) + sum(
        1 for v in unique if v.get("type") == "security_header"
    ):
        actions.append("Harden HTTP security headers on all live subdomains.")
    if by_category.get("attack_surface", 0):
        actions.append("Manually review exposed paths for authentication bypass or data leaks.")
    if by_category.get("injection", 0) or sum(1 for v in unique if v.get("type") == "sqli"):
        actions.append("Review SQL injection findings with manual confirmation (sqlmap/Burp) on in-scope hosts only.")
    if len(by_host) > 1:
        actions.append(f"Re-test {len(by_host)} hosts individually in Burp with session/auth context.")
    if not actions:
        actions.append("No high-severity automated hits; continue with manual testing on live subdomains.")

    hosts_meta = []
    if hosts_scan.exists():
        for row in json.loads(hosts_scan.read_text()).get("hosts", []):
            hosts_meta.append(
                {
                    "host": row.get("host"),
                    "url": row.get("url"),
                    "live": row.get("live"),
                    "status_code": row.get("status_code"),
                    "title": row.get("title"),
                    "findings_count": row.get("findings_count", 0),
                }
            )

    return {
        "total": len(unique),
        "by_severity": dict(by_severity),
        "by_category": dict(by_category),
        "by_host": {k: v[:25] for k, v in by_host.items()},
        "hosts_summary": hosts_meta,
        "recommended_actions": actions,
        "items": unique[:150],
    }


def main() -> int:
    workdir = Path(sys.argv[1])
    summary = aggregate(workdir)
    (workdir / "vulnerabilities.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
