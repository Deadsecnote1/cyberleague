#!/usr/bin/env python3
"""Local-only pentest dashboard — binds to 127.0.0.1 only."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from portal.n8n_engine import (
    N8nConfig,
    build_scan_payload,
    list_executions,
    n8n_health,
    trigger_scan,
)
from portal.scan_presets import PRESETS, form_from_preset
from portal.scan_catalog import (
    REPORTS_DIR,
    ROOT,
    dashboard_stats,
    delete_scan_run,
    deletion_preview,
    list_reports,
    list_runs,
    load_run_detail,
)

PORTAL_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
import scope_utils as scope  # noqa: E402

SCOPES_DIR = ROOT / "config" / "scopes"

app = FastAPI(title="Cyber League", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=PORTAL_DIR / "static"), name="static")
templates = Jinja2Templates(directory=PORTAL_DIR / "templates")


def fmt_time(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


templates.env.filters["fmt_time"] = fmt_time


def list_scope_file_presets() -> list[dict[str, str]]:
    if not SCOPES_DIR.is_dir():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(SCOPES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "file": path.name,
                    "label": data.get("program") or path.stem.replace("-", " ").title(),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return items


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, deleted: str | None = None, delete_error: str | None = None):
    runs = list_runs()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "runs": runs,
            "stats": dashboard_stats(runs),
            "reports": list_reports()[:15],
            "deleted_run_id": deleted,
            "delete_error": delete_error,
        },
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str):
    if ".." in run_id or "/" in run_id:
        raise HTTPException(404)
    detail = load_run_detail(run_id)
    if not detail:
        raise HTTPException(404, "Scan run not found")
    preview = deletion_preview(run_id)
    return templates.TemplateResponse(
        request,
        "run.html",
        {
            **detail,
            "run_id": run_id,
            "delete_preview": preview,
        },
    )


@app.post("/runs/{run_id}/delete")
async def delete_run(run_id: str, confirm: str = Form(...)):
    if ".." in run_id or "/" in run_id:
        raise HTTPException(404)
    if confirm.strip() != run_id:
        raise HTTPException(400, "Type the run id to confirm deletion")
    result = delete_scan_run(run_id)
    if not result.get("ok"):
        err = "; ".join(result.get("errors") or []) or result.get("error", "Delete failed")
        return RedirectResponse(
            url=f"/?delete_error={quote(err, safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/?deleted={run_id}", status_code=303)


@app.get("/reports", response_class=HTMLResponse)
async def reports_list(request: Request):
    return templates.TemplateResponse(
        request,
        "reports.html",
        {"reports": list_reports()},
    )


@app.get("/reports/file/{name}")
async def report_file(name: str):
    if ".." in name or "/" in name:
        raise HTTPException(404)
    path = REPORTS_DIR / name
    if not path.is_file():
        raise HTTPException(404)
    media = "text/html" if name.endswith(".html") else "text/markdown"
    return FileResponse(path, media_type=media)


@app.get("/scan", response_class=HTMLResponse)
async def scan_form(request: Request, preset: str | None = None, result: str | None = None):
    cfg = N8nConfig.load()
    n8n = n8n_health(cfg)
    form = form_from_preset(preset)
    ctx = {
        "n8n_ok": n8n.get("ok"),
        "n8n": n8n,
        "webhook_url": f"{cfg.base_url}/webhook/{cfg.webhook_path}",
        "form": form,
        "presets": PRESETS,
        "active_preset": preset or form.get("preset", "quick"),
        "scope_presets": list_scope_file_presets(),
        "scope_modes": scope.SCOPE_MODES,
        "result": None,
    }
    return templates.TemplateResponse(request, "scan_new.html", ctx)


@app.post("/scan", response_class=HTMLResponse)
async def scan_start(
    request: Request,
    target_url: str = Form(...),
    program: str = Form(""),
    profile: str = Form("light"),
    max_hosts: int = Form(5),
    request_delay_ms: int = Form(500),
    requests_per_minute: int = Form(30),
    max_runtime_minutes: int = Form(20),
    ffuf_per_host: str | None = Form(None),
    nuclei_per_host: str | None = Form(None),
    scan_all_subdomains: str | None = Form(None),
    sqli_scan: str | None = Form(None),
    ai_advisor: str | None = Form(None),
    preset: str = Form("quick"),
    scope_mode: str = Form("subdomains"),
    in_scope_hosts: str = Form(""),
    out_of_scope_hosts: str = Form(""),
    scope_notes: str = Form(""),
):
    cfg = N8nConfig.load()
    scope_cfg = scope.scope_from_form(
        target_url, scope_mode, in_scope_hosts, out_of_scope_hosts, scope_notes, program
    )
    ok, err = scope.validate_target_url(target_url, scope_cfg)
    form_data = {
        "target_url": target_url,
        "program": program,
        "scope_mode": scope_mode,
        "in_scope_hosts": in_scope_hosts,
        "out_of_scope_hosts": out_of_scope_hosts,
        "scope_notes": scope_notes,
        "profile": profile,
        "max_hosts": max_hosts,
        "request_delay_ms": request_delay_ms,
        "requests_per_minute": requests_per_minute,
        "max_runtime_minutes": max_runtime_minutes,
        "ffuf_per_host": ffuf_per_host is not None,
        "nuclei_per_host": nuclei_per_host is not None,
        "scan_all_subdomains": scan_all_subdomains is not None,
        "sqli_scan": sqli_scan is not None,
        "ai_advisor": ai_advisor is not None,
        "preset": preset,
    }
    if not ok:
        result = {"ok": False, "message": err, "hint": "Adjust pentest scope or target URL."}
    else:
        payload = build_scan_payload(
            target_url=target_url,
            program=program,
            scope=scope_cfg,
            profile=profile,
            max_hosts=max_hosts,
            request_delay_ms=request_delay_ms,
            requests_per_minute=requests_per_minute,
            max_runtime_minutes=max_runtime_minutes,
            ffuf_per_host=ffuf_per_host is not None,
            nuclei_per_host=nuclei_per_host is not None,
            scan_all_subdomains=scan_all_subdomains is not None,
            sqli_scan=sqli_scan is not None,
            ai_advisor=ai_advisor is not None,
        )
        result = trigger_scan(payload)
    return templates.TemplateResponse(
        request,
        "scan_new.html",
        {
            "n8n_ok": n8n_health(cfg).get("ok"),
            "n8n": n8n_health(cfg),
            "webhook_url": f"{cfg.base_url}/webhook/{cfg.webhook_path}",
            "form": form_data,
            "presets": PRESETS,
            "active_preset": preset,
            "scope_presets": list_scope_file_presets(),
            "scope_modes": scope.SCOPE_MODES,
            "result": result,
        },
    )


@app.get("/api/scope-preset/{filename}")
async def scope_preset_json(filename: str):
    if ".." in filename or "/" in filename or not filename.endswith(".json"):
        raise HTTPException(404)
    path = SCOPES_DIR / filename
    if not path.is_file():
        raise HTTPException(404)
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/executions", response_class=HTMLResponse)
async def executions_page(request: Request):
    cfg = N8nConfig.load()
    return templates.TemplateResponse(
        request,
        "executions.html",
        {
            "executions": list_executions(25, cfg),
            "workflow_id": cfg.workflow_id,
        },
    )


@app.get("/health")
async def health():
    cfg = N8nConfig.load()
    return {"ok": True, "root": str(ROOT), "n8n": n8n_health(cfg)}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "portal.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
