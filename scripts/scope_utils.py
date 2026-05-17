#!/usr/bin/env python3
"""Pentest / bug-bounty scope parsing, validation, and host filtering."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCOPE_MODES = ("apex_only", "subdomains", "custom")


def normalize_host(host: str) -> str:
    host = (host or "").strip().lower()
    host = host.replace("https://", "").replace("http://", "")
    if host.startswith("www."):
        host = host[4:]
    host = host.split("/")[0].split(":")[0].strip(".")
    return host


def domain_from_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    try:
        return normalize_host(urlparse(raw).netloc or raw)
    except Exception:
        return normalize_host(raw)


def parse_host_lines(text: str) -> list[str]:
    hosts: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Allow URLs in scope lists
        h = domain_from_url(line) if "://" in line or "/" in line else normalize_host(line)
        if h and "." in h and h not in hosts:
            hosts.append(h)
    return hosts


def host_matches_pattern(host: str, pattern: str) -> bool:
    host = normalize_host(host)
    pattern = normalize_host(pattern.replace("*.", ""))
    if not host or not pattern:
        return False
    raw_pat = (pattern if "://" not in pattern else domain_from_url(pattern)).strip().lower()
    if raw_pat.startswith("*."):
        suffix = raw_pat[2:]
        return host == suffix or host.endswith("." + suffix)
    if raw_pat.startswith("*"):
        suffix = raw_pat[1:].lstrip(".")
        return host == suffix or host.endswith("." + suffix)
    return host == raw_pat


def build_scope(
    *,
    target_url: str,
    mode: str = "subdomains",
    in_scope: list[str] | None = None,
    out_of_scope: list[str] | None = None,
    notes: str = "",
    program: str = "",
) -> dict[str, Any]:
    root = domain_from_url(target_url)
    mode = (mode or "subdomains").lower().strip()
    if mode not in SCOPE_MODES:
        mode = "subdomains"

    explicit_in = list(in_scope or [])
    explicit_out = list(out_of_scope or [])

    if mode == "apex_only":
        allowed_patterns = [root] if root else []
    elif mode == "custom":
        allowed_patterns = explicit_in if explicit_in else ([root] if root else [])
    else:  # subdomains
        allowed_patterns = []
        if root:
            allowed_patterns.extend([root, f"*.{root}"])
        allowed_patterns.extend(explicit_in)

    # Dedupe while preserving order
    seen: set[str] = set()
    patterns: list[str] = []
    for p in allowed_patterns:
        p = p.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        patterns.append(p)

    out_seen: set[str] = set()
    exclusions: list[str] = []
    for p in explicit_out:
        if p and p not in out_seen:
            out_seen.add(p)
            exclusions.append(p)

    return {
        "root_domain": root,
        "mode": mode,
        "in_scope": patterns,
        "out_of_scope": exclusions,
        "notes": (notes or "").strip(),
        "program": (program or "").strip(),
        "target_url": (target_url or "").strip(),
    }


def is_host_in_scope(host: str, scope: dict[str, Any]) -> bool:
    host = normalize_host(host)
    if not host or not scope.get("root_domain"):
        return False

    exclusions = scope.get("out_of_scope") or []
    for pat in exclusions:
        if host_matches_pattern(host, pat):
            return False

    patterns = scope.get("in_scope") or []
    if not patterns:
        root = scope.get("root_domain", "")
        if scope.get("mode") == "apex_only":
            return host == root
        return host == root or host.endswith("." + root)

    for pat in patterns:
        if host_matches_pattern(host, pat):
            return True
    return False


def validate_target_url(target_url: str, scope: dict[str, Any]) -> tuple[bool, str]:
    host = domain_from_url(target_url)
    if not host or "." not in host:
        return False, "Enter a valid target URL or domain."
    if not scope.get("root_domain"):
        scope["root_domain"] = host
    if not is_host_in_scope(host, scope):
        allowed = ", ".join(scope.get("in_scope") or []) or scope.get("root_domain", "")
        return False, f"Target host '{host}' is outside the configured scope ({allowed})."
    return True, ""


def filter_hosts(hosts: list[str], scope: dict[str, Any]) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for h in hosts:
        h = normalize_host(h)
        if not h or h in seen:
            continue
        seen.add(h)
        if is_host_in_scope(h, scope):
            allowed.append(h)
        else:
            rejected.append(h)
    return allowed, rejected


def filter_workdir(workdir: Path, scope: dict[str, Any] | None = None) -> dict[str, Any]:
    workdir = Path(workdir)
    scope_path = workdir / "scope.json"
    if scope is None:
        if not scope_path.exists():
            return {"ok": True, "skipped": True}
        scope = json.loads(scope_path.read_text(encoding="utf-8"))

    summary: dict[str, Any] = {
        "ok": True,
        "mode": scope.get("mode"),
        "root_domain": scope.get("root_domain"),
        "filtered": {},
    }

    for name in ("subdomains.txt", "hosts.txt"):
        path = workdir / name
        if not path.exists():
            continue
        hosts = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        kept, rejected = filter_hosts(hosts, scope)
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        summary["filtered"][name] = {"kept": len(kept), "rejected": len(rejected)}
        if rejected:
            summary.setdefault("rejected_hosts", []).extend(rejected)

    rejected_all = sorted(set(summary.get("rejected_hosts") or []))
    if rejected_all:
        (workdir / "scope_rejected.json").write_text(
            json.dumps({"rejected": rejected_all, "scope": scope}, indent=2),
            encoding="utf-8",
        )
        summary["rejected_hosts"] = rejected_all
    return summary


def scope_from_form(
    target_url: str,
    scope_mode: str,
    in_scope_text: str,
    out_of_scope_text: str,
    scope_notes: str,
    program: str,
) -> dict[str, Any]:
    return build_scope(
        target_url=target_url,
        mode=scope_mode,
        in_scope=parse_host_lines(in_scope_text),
        out_of_scope=parse_host_lines(out_of_scope_text),
        notes=scope_notes,
        program=program,
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scope_utils.py filter-workdir <workdir>", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "filter-workdir":
        if len(sys.argv) < 3:
            print("missing workdir", file=sys.stderr)
            return 1
        result = filter_workdir(Path(sys.argv[2]))
        print(json.dumps(result))
        return 0
    if cmd == "check-host":
        scope = json.loads(sys.argv[2])
        host = sys.argv[3]
        print("true" if is_host_in_scope(host, scope) else "false")
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
