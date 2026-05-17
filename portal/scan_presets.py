"""Scan configuration presets for the Cyber League portal."""

from __future__ import annotations

from typing import Any

# Default for new scans and n8n form fallbacks
QUICK: dict[str, Any] = {
    "profile": "light",
    "max_hosts": 5,
    "sqli_scan": True,
    "ffuf_per_host": False,
    "nuclei_per_host": False,
    "scan_all_subdomains": True,
    "request_delay_ms": 500,
    "requests_per_minute": 30,
    "ai_advisor": True,
    "max_runtime_minutes": 20,
    "label": "Quick",
    "eta": "~5–15 min",
    "description": "Subdomain discovery, headers, web checks. No per-host FFUF/Nuclei.",
}

STANDARD: dict[str, Any] = {
    "profile": "light",
    "max_hosts": 10,
    "sqli_scan": True,
    "ffuf_per_host": True,
    "nuclei_per_host": False,
    "scan_all_subdomains": True,
    "request_delay_ms": 500,
    "requests_per_minute": 30,
    "ai_advisor": True,
    "max_runtime_minutes": 35,
    "label": "Standard",
    "eta": "~15–30 min",
    "description": "Light profile with FFUF on up to 10 hosts.",
}

DEEP: dict[str, Any] = {
    "profile": "both",
    "max_hosts": 15,
    "sqli_scan": True,
    "ffuf_per_host": True,
    "nuclei_per_host": True,
    "scan_all_subdomains": True,
    "request_delay_ms": 500,
    "requests_per_minute": 30,
    "ai_advisor": True,
    "max_runtime_minutes": 90,
    "label": "Deep",
    "eta": "~45–90+ min",
    "description": "Light + deep (nmap, nuclei, nikto). Full per-host tooling.",
}

PRESETS: dict[str, dict[str, Any]] = {
    "quick": QUICK,
    "standard": STANDARD,
    "deep": DEEP,
}

DEFAULT_PRESET = "quick"


def get_preset(name: str | None) -> dict[str, Any]:
    key = (name or DEFAULT_PRESET).lower().strip()
    return dict(PRESETS.get(key, QUICK))


def form_from_preset(name: str | None, target_url: str = "", program: str = "") -> dict[str, Any]:
    p = get_preset(name)
    domain = target_url.replace("https://", "").replace("http://", "").split("/")[0] if target_url else ""
    default_in_scope = f"{domain}\n*.{domain}" if domain and "." in domain else ""
    return {
        "target_url": target_url,
        "program": program,
        "scope_mode": "subdomains",
        "in_scope_hosts": default_in_scope,
        "out_of_scope_hosts": "",
        "scope_notes": "",
        "profile": p["profile"],
        "max_hosts": p["max_hosts"],
        "sqli_scan": p.get("sqli_scan", True),
        "ffuf_per_host": p["ffuf_per_host"],
        "nuclei_per_host": p["nuclei_per_host"],
        "scan_all_subdomains": p["scan_all_subdomains"],
        "request_delay_ms": p["request_delay_ms"],
        "requests_per_minute": p["requests_per_minute"],
        "ai_advisor": p["ai_advisor"],
        "preset": name or DEFAULT_PRESET,
        "max_runtime_minutes": p.get("max_runtime_minutes", 0),
    }
