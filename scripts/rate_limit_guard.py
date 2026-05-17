#!/usr/bin/env python3
"""
Rate limiting and IP/WAF block detection for the pentest pipeline.

State is stored in <workdir>/guard_state.json. When a block is detected,
writes .scan_stop and sets blocked=true so all scan stages exit cleanly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WAF_MARKERS = re.compile(
    r"cloudflare|cf-ray|akamai|incapsula|sucuri|perimeterx|"
    r"attention required|access denied|request blocked|"
    r"your ip has been|banned|rate limit|too many requests|"
    r"ddos protection|bot protection|captcha|challenge-platform",
    re.I,
)

BLOCK_STATUS_CODES = {429, 403, 503, 520, 521, 522, 523, 524}


def state_path(workdir: Path) -> Path:
    return workdir / "guard_state.json"


def stop_path(workdir: Path) -> Path:
    return workdir / ".scan_stop"


def default_state() -> dict[str, Any]:
    return {
        "blocked": False,
        "rate_limited": False,
        "requests": 0,
        "window_start": time.time(),
        "consecutive_blocks": 0,
        "events": [],
        "tester_message": "",
        "recommendations": [],
    }


def load_state(workdir: Path) -> dict[str, Any]:
    p = state_path(workdir)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return {**default_state(), **data}
        except json.JSONDecodeError:
            pass
    return default_state()


def save_state(workdir: Path, state: dict[str, Any]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    state_path(workdir).write_text(json.dumps(state, indent=2), encoding="utf-8")


def delay_ms() -> int:
    return max(0, int(os.environ.get("REQUEST_DELAY_MS", "500")))


def requests_per_minute() -> int:
    return max(1, int(os.environ.get("REQUESTS_PER_MINUTE", "30")))


def block_threshold() -> int:
    return max(1, int(os.environ.get("BLOCK_CONSECUTIVE_THRESHOLD", "3")))


def sleep_rate_limit(workdir: Path | None = None) -> None:
    ms = delay_ms()
    if ms > 0:
        time.sleep(ms / 1000.0)
    if workdir is None:
        return
    state = load_state(workdir)
    now = time.time()
    if now - state.get("window_start", now) > 60:
        state["window_start"] = now
        state["requests"] = 0
    state["requests"] = int(state.get("requests", 0)) + 1
    rpm = requests_per_minute()
    if state["requests"] > rpm:
        wait = 60 - (now - state["window_start"])
        if wait > 0:
            time.sleep(wait)
        state["window_start"] = time.time()
        state["requests"] = 1
    save_state(workdir, state)


def _append_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    events = state.setdefault("events", [])
    events.append(event)
    state["events"] = events[-30:]


def detect_block(
    *,
    url: str,
    status_code: int | None,
    headers: dict[str, str] | None = None,
    body_snippet: str = "",
    tool: str = "http",
    error: str = "",
) -> tuple[bool, str]:
    headers = headers or {}
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items())
    combined = f"{header_blob} {body_snippet} {error}"

    if status_code == 429:
        return True, f"HTTP 429 Too Many Requests from {url} ({tool})"

    if status_code in BLOCK_STATUS_CODES and WAF_MARKERS.search(combined):
        return True, f"WAF/block page detected (HTTP {status_code}) on {url} ({tool})"

    if status_code == 403 and tool in ("httpx", "curl", "http", "ffuf", "nuclei"):
        # Single 403 may be path-specific; counted via consecutive_blocks
        if WAF_MARKERS.search(combined):
            return True, f"Access blocked (HTTP 403) on {url} ({tool})"

    if error and re.search(r"timed out|connection refused|no route|network unreachable", error, re.I):
        if "connection refused" in error.lower():
            return False, ""  # target down, not necessarily IP block

    if re.search(r"ssl.*alert|handshake failure", error, re.I):
        return False, ""

    return False, ""


def record_probe(
    workdir: Path,
    *,
    url: str,
    status_code: int | None = None,
    headers: dict[str, str] | None = None,
    body_snippet: str = "",
    tool: str = "http",
    error: str = "",
) -> dict[str, Any]:
    state = load_state(workdir)
    if state.get("blocked"):
        return state

    is_block, reason = detect_block(
        url=url,
        status_code=status_code,
        headers=headers,
        body_snippet=body_snippet,
        tool=tool,
        error=error,
    )

    suspicious = status_code in (403, 429, 503) or is_block
    if suspicious:
        state["consecutive_blocks"] = int(state.get("consecutive_blocks", 0)) + 1
        _append_event(
            state,
            {
                "ts": time.time(),
                "url": url,
                "status": status_code,
                "tool": tool,
                "reason": reason or f"HTTP {status_code}",
            },
        )
    else:
        state["consecutive_blocks"] = 0

    if is_block or state["consecutive_blocks"] >= block_threshold():
        state["blocked"] = True
        state["rate_limited"] = status_code == 429 or "429" in (reason or "")
        state["tester_message"] = (
            reason
            if is_block
            else (
                f"Target appears to be blocking this IP: {state['consecutive_blocks']} "
                f"consecutive block-like responses (403/429/503). Stopping all scans."
            )
        )
        state["recommendations"] = [
            "Stop scanning immediately to avoid further blocking or program violation.",
            "Wait 24–72 hours or switch to a VPN/egress IP approved for testing.",
            "Contact the program owner if you believe this is a false positive.",
            "Retry with Scan profile=light, lower Max subdomain hosts, and higher Request delay.",
        ]
        stop_path(workdir).write_text(state["tester_message"], encoding="utf-8")
        save_state(workdir, state)
        return state

    save_state(workdir, state)
    return state


def should_stop(workdir: Path) -> bool:
    if stop_path(workdir).exists():
        return True
    return bool(load_state(workdir).get("blocked"))


def analyze_httpx_json(workdir: Path) -> dict[str, Any]:
    live_json = workdir / "live.json"
    if not live_json.exists():
        return load_state(workdir)
    for line in live_json.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = row.get("url") or row.get("final_url") or ""
        status = row.get("status_code") or row.get("status-code")
        if isinstance(status, str) and status.isdigit():
            status = int(status)
        headers = {}
        for k, v in (row.get("header") or row.get("headers") or {}).items():
            headers[str(k).lower()] = str(v)
        body = str(row.get("body") or row.get("response") or "")[:500]
        record_probe(
            workdir,
            url=url or str(row.get("input", "")),
            status_code=status if isinstance(status, int) else None,
            headers=headers,
            body_snippet=body,
            tool="httpx",
        )
        if should_stop(workdir):
            break
    return load_state(workdir)


def probe_url(workdir: Path, url: str, timeout: int = 20) -> dict[str, Any]:
    sleep_rate_limit(workdir)
    status_code = None
    headers: dict[str, str] = {}
    body = ""
    err = ""
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "BugBountyPipeline/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except HTTPError as exc:
        status_code = exc.code
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        try:
            body = exc.read(500).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        err = str(exc)
    except URLError as exc:
        err = str(exc.reason if hasattr(exc, "reason") else exc)
    except Exception as exc:
        err = str(exc)
    return record_probe(
        workdir,
        url=url,
        status_code=status_code,
        headers=headers,
        body_snippet=body,
        tool="curl",
        error=err,
    )


def block_summary(workdir: Path) -> dict[str, Any]:
    state = load_state(workdir)
    return {
        "blocked": bool(state.get("blocked")),
        "rate_limited": bool(state.get("rate_limited")),
        "tester_message": state.get("tester_message", ""),
        "recommendations": state.get("recommendations", []),
        "events": state.get("events", [])[-10:],
        "consecutive_blocks": state.get("consecutive_blocks", 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rate limit and IP block guard")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sleep = sub.add_parser("sleep")
    p_sleep.add_argument("workdir", nargs="?", default="")

    p_stop = sub.add_parser("should-stop")
    p_stop.add_argument("workdir")

    p_probe = sub.add_parser("probe")
    p_probe.add_argument("workdir")
    p_probe.add_argument("--url", required=True)
    p_probe.add_argument("--status", type=int, default=None)
    p_probe.add_argument("--tool", default="http")
    p_probe.add_argument("--error", default="")

    p_httpx = sub.add_parser("analyze-httpx")
    p_httpx.add_argument("workdir")

    p_url = sub.add_parser("probe-url")
    p_url.add_argument("workdir")
    p_url.add_argument("url")

    p_sum = sub.add_parser("summary")
    p_sum.add_argument("workdir")

    args = parser.parse_args()

    if args.cmd == "sleep":
        wd = Path(args.workdir) if args.workdir else None
        sleep_rate_limit(wd)
        return 0

    wd = Path(args.workdir)

    if args.cmd == "should-stop":
        print("true" if should_stop(wd) else "false")
        return 0

    if args.cmd == "probe":
        record_probe(
            wd,
            url=args.url,
            status_code=args.status,
            tool=args.tool,
            error=args.error,
        )
        print(json.dumps(block_summary(wd)))
        return 0

    if args.cmd == "analyze-httpx":
        analyze_httpx_json(wd)
        print(json.dumps(block_summary(wd)))
        return 0

    if args.cmd == "probe-url":
        probe_url(wd, args.url)
        print(json.dumps(block_summary(wd)))
        return 0

    if args.cmd == "summary":
        print(json.dumps(block_summary(wd)))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
