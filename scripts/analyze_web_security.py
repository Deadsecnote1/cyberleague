#!/usr/bin/env python3
"""Analyze HTTP headers, cookies, and TLS for common security issues."""

from __future__ import annotations

import json
import re
import socket
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_headers(url: str, timeout: int = 20) -> tuple[dict[str, str], str]:
    req = Request(url, method="HEAD", headers={"User-Agent": "BugBountyPipeline/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return headers, url
    except Exception:
        req = Request(url, headers={"User-Agent": "BugBountyPipeline/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return headers, resp.geturl()


def check_headers(headers: dict[str, str]) -> list[dict]:
    findings: list[dict] = []
    required = {
        "strict-transport-security": ("missing_hsts", "medium", "Missing Strict-Transport-Security"),
        "content-security-policy": ("missing_csp", "low", "Missing Content-Security-Policy"),
        "x-frame-options": ("missing_x_frame_options", "low", "Missing X-Frame-Options (clickjacking)"),
        "x-content-type-options": ("missing_x_content_type_options", "low", "Missing X-Content-Type-Options"),
        "referrer-policy": ("missing_referrer_policy", "info", "Missing Referrer-Policy"),
        "permissions-policy": (
            "missing_permissions_policy",
            "info",
            "Missing Permissions-Policy",
        ),
    }
    for header, (code, severity, title) in required.items():
        if header not in headers:
            findings.append(
                {
                    "severity": severity,
                    "title": title,
                    "type": "security_header",
                    "code": code,
                    "source": "header_analysis",
                }
            )
    server = headers.get("server", "")
    if server and re.search(r"(apache|nginx|iis)/[\d.]+", server, re.I):
        findings.append(
            {
                "severity": "info",
                "title": f"Server version disclosed: {server[:80]}",
                "type": "information_disclosure",
                "code": "server_version_disclosure",
                "source": "header_analysis",
            }
        )
    return findings


def check_cookies(headers: dict[str, str]) -> list[dict]:
    findings: list[dict] = []
    raw = headers.get("set-cookie", "")
    if not raw:
        return findings
    cookies = re.split(r", (?=[^;]+=)", raw) if "," in raw else [raw]
    for chunk in cookies:
        name = chunk.split("=", 1)[0].strip()
        lower = chunk.lower()
        issues = []
        if "secure" not in lower:
            issues.append("no Secure")
        if "httponly" not in lower:
            issues.append("no HttpOnly")
        if "samesite" not in lower:
            issues.append("no SameSite")
        if issues:
            findings.append(
                {
                    "severity": "medium",
                    "title": f"Insecure cookie flags on '{name}': {', '.join(issues)}",
                    "type": "cookie",
                    "code": "insecure_cookie",
                    "source": "cookie_analysis",
                }
            )
    return findings


def check_tls(domain: str, port: int = 443) -> list[dict]:
    findings: list[dict] = []
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=12) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol = ssock.version() or "unknown"
        if protocol in {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}:
            findings.append(
                {
                    "severity": "high",
                    "title": f"Weak TLS protocol negotiated: {protocol}",
                    "type": "tls",
                    "code": "weak_tls_protocol",
                    "source": "tls_analysis",
                }
            )
        not_after = cert.get("notAfter")
        if not_after:
            exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                findings.append(
                    {
                        "severity": "high",
                        "title": "TLS certificate expired",
                        "type": "tls",
                        "code": "cert_expired",
                        "source": "tls_analysis",
                    }
                )
            days = (exp - datetime.now(timezone.utc)).days
            if 0 < days < 30:
                findings.append(
                    {
                        "severity": "medium",
                        "title": f"TLS certificate expires in {days} days",
                        "type": "tls",
                        "code": "cert_expiring_soon",
                        "source": "tls_analysis",
                    }
                )
    except ssl.SSLCertVerificationError:
        findings.append(
            {
                "severity": "high",
                "title": "TLS certificate verification failed",
                "type": "tls",
                "code": "cert_untrusted",
                "source": "tls_analysis",
            }
        )
    except Exception as exc:  # noqa: BLE001
        findings.append(
            {
                "severity": "info",
                "title": f"TLS check skipped: {exc}",
                "type": "tls",
                "code": "tls_check_error",
                "source": "tls_analysis",
            }
        )
    return findings


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: analyze_web_security.py <domain> <workdir> [primary_url]", file=sys.stderr)
        return 1
    domain, workdir, *rest = sys.argv[1:]
    wd = Path(workdir)
    primary = rest[0] if rest else f"https://{domain}"

    findings: list[dict] = []
    for url in {primary, f"https://{domain}", f"http://{domain}"}:
        try:
            headers, final_url = fetch_headers(url)
            findings.extend(check_headers(headers))
            findings.extend(check_cookies(headers))
            break
        except Exception:
            continue

    findings.extend(check_tls(domain))

    # dedupe by code+title
    seen: set[str] = set()
    unique: list[dict] = []
    for f in findings:
        key = f"{f.get('code')}::{f.get('title')}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    out = {"findings": unique, "count": len(unique)}
    (wd / "web_security.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
