"""Trigger and monitor scans via n8n (engine). Scripts run only inside n8n nodes."""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portal.scan_presets import QUICK

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "portal" / "n8n_config.json"
N8N_DB = Path.home() / ".n8n" / "database.sqlite"


@dataclass
class N8nConfig:
    base_url: str
    workflow_id: str
    webhook_path: str
    form_webhook_id: str

    @classmethod
    def load(cls) -> N8nConfig:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        else:
            wf_id = (ROOT / ".workflow_id").read_text(encoding="utf-8").strip()
            data = {
                "base_url": "http://localhost:5678",
                "workflow_id": wf_id,
                "webhook_path": "portal-scan",
                "form_webhook_id": "6436c3d3-a7dc-4a56-8c3c-985792afdddb",
            }
        return cls(
            base_url=data.get("base_url", "http://localhost:5678").rstrip("/"),
            workflow_id=data["workflow_id"],
            webhook_path=data.get("webhook_path", "portal-scan"),
            form_webhook_id=data.get("form_webhook_id", ""),
        )


def n8n_health(cfg: N8nConfig | None = None) -> dict[str, Any]:
    cfg = cfg or N8nConfig.load()
    try:
        req = urllib.request.Request(f"{cfg.base_url}/healthz", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"ok": resp.status == 200, "status": resp.status, "base_url": cfg.base_url}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "base_url": cfg.base_url}


def build_scan_payload(
    *,
    target_url: str,
    program: str = "",
    scope: dict[str, Any] | None = None,
    profile: str | None = None,
    max_hosts: int | None = None,
    ffuf_per_host: bool | None = None,
    nuclei_per_host: bool | None = None,
    scan_all_subdomains: bool | None = None,
    sqli_scan: bool | None = None,
    ai_advisor: bool | None = None,
    request_delay_ms: int | None = None,
    requests_per_minute: int | None = None,
    max_runtime_minutes: int | None = None,
) -> dict[str, Any]:
    defaults = QUICK
    profile = (profile or defaults["profile"]).lower()
    max_hosts = max_hosts if max_hosts is not None else int(defaults["max_hosts"])
    ffuf = defaults["ffuf_per_host"] if ffuf_per_host is None else ffuf_per_host
    nuclei = defaults["nuclei_per_host"] if nuclei_per_host is None else nuclei_per_host
    all_subs = defaults["scan_all_subdomains"] if scan_all_subdomains is None else scan_all_subdomains
    sqli = defaults.get("sqli_scan", True) if sqli_scan is None else sqli_scan
    ai = defaults["ai_advisor"] if ai_advisor is None else ai_advisor
    delay = request_delay_ms if request_delay_ms is not None else int(defaults["request_delay_ms"])
    rpm = requests_per_minute if requests_per_minute is not None else int(defaults["requests_per_minute"])
    runtime = max_runtime_minutes if max_runtime_minutes is not None else int(defaults.get("max_runtime_minutes", 0))
    payload: dict[str, Any] = {
        "target_url": target_url.strip(),
        "program": program.strip() or "portal",
        "scan_config": {
            "profile": profile,
            "max_hosts": max_hosts,
            "ffuf_per_host": ffuf,
            "nuclei_per_host": nuclei,
            "scan_all_subdomains": all_subs,
            "sqli_scan": sqli,
            "request_delay_ms": delay,
            "requests_per_minute": rpm,
            "max_runtime_minutes": runtime,
        },
        "enable_ai": ai,
    }
    if scope:
        payload["scope"] = scope
    return payload


def trigger_scan_webhook(payload: dict[str, Any], cfg: N8nConfig | None = None) -> dict[str, Any]:
    """POST JSON to n8n Portal Scan webhook (preferred)."""
    cfg = cfg or N8nConfig.load()
    url = f"{cfg.base_url}/webhook/{cfg.webhook_path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                data = {"raw": raw[:2000]}
            return {
                "ok": True,
                "method": "webhook",
                "url": url,
                "status": resp.status,
                "response": data,
            }
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:1500]
        return {
            "ok": False,
            "method": "webhook",
            "url": url,
            "status": exc.code,
            "error": err or str(exc),
            "hint": _webhook_hint(exc.code),
        }
    except Exception as exc:
        return {"ok": False, "method": "webhook", "url": url, "error": str(exc)}


def trigger_scan_form(payload: dict[str, Any], cfg: N8nConfig | None = None) -> dict[str, Any]:
    """Fallback: n8n form trigger (multipart)."""
    cfg = cfg or N8nConfig.load()
    if not cfg.form_webhook_id:
        return {"ok": False, "error": "form_webhook_id not configured"}
    url = f"{cfg.base_url}/form/{cfg.form_webhook_id}"
    sc = payload.get("scan_config") or {}
    # n8n Form Trigger v2 expects multipart keys field-0, field-1, … (not field labels).
    field_values = {
        "Target URL": payload.get("target_url", ""),
        "Program name (optional)": payload.get("program", ""),
        "Max subdomain hosts": str(sc.get("max_hosts", 5)),
        "FFUF per host": "Yes" if sc.get("ffuf_per_host", False) else "No",
        "Nuclei per host": "Yes" if sc.get("nuclei_per_host", False) else "No",
        "Scan all subdomains": "Yes" if sc.get("scan_all_subdomains", True) else "No",
        "Scan profile": sc.get("profile", "light"),
        "Enable AI hunt advisor": "Yes" if payload.get("enable_ai", True) else "No",
    }
    fields = {f"field-{i}": v for i, v in enumerate(field_values.values())}
    body, content_type = _encode_multipart_form(fields)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "ok": True,
                "method": "form",
                "url": url,
                "status": resp.status,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "method": "form",
            "url": url,
            "status": exc.code,
            "error": exc.read().decode("utf-8", errors="replace")[:1000],
            "hint": _webhook_hint(exc.code),
        }


def _write_scan_sidecar(payload: dict[str, Any]) -> None:
    """Persist domain + scan env for n8n Run Pentest (expression / arg workaround)."""
    url = (payload.get("target_url") or "").strip()
    sc = payload.get("scan_config") or {}
    lines: list[str] = []
    if url:
        domain = (
            url.replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .split("/")[0]
            .split(":")[0]
            .lower()
        )
        if domain and "." in domain:
            (ROOT / ".current_scan_domain").write_text(domain + "\n", encoding="utf-8")
    profile = sc.get("profile", "light")
    max_hosts = int(sc.get("max_hosts", 5))
    lines.extend(
        [
            f"SCAN_PROFILE={profile}",
            f"MAX_SUBDOMAIN_SCANS={max_hosts}",
            f"FFUF_PER_HOST={'1' if sc.get('ffuf_per_host') else '0'}",
            f"NUCLEI_PER_HOST={'1' if sc.get('nuclei_per_host') else '0'}",
            f"SCAN_ALL_SUBDOMAINS={'1' if sc.get('scan_all_subdomains', True) else '0'}",
            f"SQLI_SCAN={'1' if sc.get('sqli_scan', True) else '0'}",
            f"REQUEST_DELAY_MS={int(sc.get('request_delay_ms', 500))}",
            f"REQUESTS_PER_MINUTE={int(sc.get('requests_per_minute', 30))}",
        ]
    )
    runtime = int(sc.get("max_runtime_minutes") or 0)
    if runtime > 0:
        lines.append(f"SCAN_MAX_RUNTIME_MINUTES={runtime}")
    (ROOT / ".current_scan_env").write_text("\n".join(lines) + "\n", encoding="utf-8")

    scope = payload.get("scope")
    if scope and isinstance(scope, dict):
        (ROOT / ".current_scan_scope.json").write_text(
            json.dumps(scope, indent=2) + "\n",
            encoding="utf-8",
        )


def trigger_scan(payload: dict[str, Any]) -> dict[str, Any]:
    """Try portal webhook first, then form trigger."""
    _write_scan_sidecar(payload)
    result = trigger_scan_webhook(payload)
    if result.get("ok"):
        return result
    form_result = trigger_scan_form(payload)
    if form_result.get("ok"):
        return form_result
    return {
        "ok": False,
        "webhook": result,
        "form": form_result,
        "message": (
            "Could not start scan via n8n. Ensure the workflow is Published/Active in n8n "
            f"({N8nConfig.load().base_url}) and the Portal Scan webhook is registered."
        ),
    }


def _encode_multipart_form(fields: dict[str, str]) -> tuple[bytes, str]:
    """n8n form triggers require multipart/form-data (not urlencoded)."""
    boundary = f"----portal{uuid.uuid4().hex}"
    buf = BytesIO()
    for name, value in fields.items():
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        buf.write(f"{value}\r\n".encode())
    buf.write(f"--{boundary}--\r\n".encode())
    return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def _webhook_hint(status: int) -> str:
    if status == 404:
        return (
            "Webhook not found. Open n8n, open 'Bug Bounty Pentest Pipeline', "
            "toggle Active off/on or click Publish, then retry."
        )
    if status == 503:
        return "n8n may be starting up; wait a few seconds and retry."
    return ""


def list_executions(limit: int = 20, cfg: N8nConfig | None = None) -> list[dict[str, Any]]:
    cfg = cfg or N8nConfig.load()
    if not N8N_DB.exists():
        return []
    conn = sqlite3.connect(N8N_DB)
    rows = conn.execute(
        """
        SELECT id, status, startedAt, stoppedAt, mode
        FROM execution_entity
        WHERE workflowId = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (cfg.workflow_id, limit),
    ).fetchall()
    return [
        {
            "id": r[0],
            "status": r[1],
            "started_at": r[2],
            "stopped_at": r[3],
            "mode": r[4],
            "n8n_url": f"{cfg.base_url}/workflow/{cfg.workflow_id}/executions/{r[0]}",
        }
        for r in rows
    ]
