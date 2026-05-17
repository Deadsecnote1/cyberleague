"""Read scan runs and reports from the project filesystem."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCANS_DIR = ROOT / "scans"
REPORTS_DIR = ROOT / "reports"

SCAN_DIR_RE = re.compile(r"^(.+)_(\d{8}T\d{6}Z)$")


@dataclass
class ScanRun:
    run_id: str
    domain: str
    stamp: str
    path: Path
    mtime: float
    total: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    blocked: bool = False
    tester_message: str = ""
    hosts_scanned: int = 0

    @property
    def started_at(self) -> datetime | None:
        try:
            return datetime.strptime(self.stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_run(run_id: str) -> ScanRun | None:
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        return None
    return parse_run_dir(SCANS_DIR / run_id)


def related_report_paths(run: ScanRun) -> list[Path]:
    """HTML/AI report files in reports/ tied to this run (matched by UTC stamp)."""
    if not REPORTS_DIR.exists():
        return []
    stamp = run.stamp
    paths: list[Path] = []
    for p in REPORTS_DIR.iterdir():
        if not p.is_file():
            continue
        name = p.name
        if stamp not in name:
            continue
        # Skip shared AI files without a stamp in the name (e.g. ai_pre_scan.md).
        if name.startswith("ai_") and stamp not in name:
            continue
        paths.append(p)
    return sorted(paths, key=lambda x: x.name)


def deletion_targets(run: ScanRun) -> list[Path]:
    """All filesystem paths removed when deleting a scan run."""
    targets = [run.path.resolve()]
    targets.extend(p.resolve() for p in related_report_paths(run))
    return targets


def deletion_preview(run_id: str) -> dict[str, Any] | None:
    run = get_run(run_id)
    if not run:
        return None
    targets = deletion_targets(run)
    return {
        "run": run,
        "targets": [str(p.relative_to(ROOT)) for p in targets],
        "scan_dir": str(run.path.relative_to(ROOT)),
        "report_files": [p.name for p in related_report_paths(run)],
        "file_count": sum(1 for _ in run.path.rglob("*") if _.is_file()) if run.path.exists() else 0,
    }


def _stop_scan_workers(workdir: Path) -> None:
    stop_file = workdir / ".scan_stop"
    try:
        stop_file.touch(exist_ok=True)
    except OSError:
        pass
    pattern = str(workdir)
    subprocess.run(
        ["pkill", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def delete_scan_run(run_id: str) -> dict[str, Any]:
    """Delete scan workdir and related reports. Returns summary for the UI."""
    run = get_run(run_id)
    if not run:
        return {"ok": False, "error": "Scan run not found", "run_id": run_id}

    if run.path.exists():
        _stop_scan_workers(run.path)

    deleted: list[str] = []
    errors: list[str] = []

    for target in deletion_targets(run):
        if not target.exists():
            continue
        rel = str(target.relative_to(ROOT))
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            deleted.append(rel)
        except OSError as exc:
            errors.append(f"{rel}: {exc}")

    return {
        "ok": not errors,
        "run_id": run_id,
        "domain": run.domain,
        "deleted": deleted,
        "errors": errors,
    }


def parse_run_dir(path: Path) -> ScanRun | None:
    m = SCAN_DIR_RE.match(path.name)
    if not m or not path.is_dir():
        return None
    domain, stamp = m.group(1), m.group(2)
    vulns = _read_json(path / "vulnerabilities.json") or {}
    guard = _read_json(path / "guard_state.json") or {}
    hosts_scan = _read_json(path / "hosts_scan.json") or {}
    blocked = bool(guard.get("blocked")) or (path / ".scan_stop").exists()
    return ScanRun(
        run_id=path.name,
        domain=domain,
        stamp=stamp,
        path=path,
        mtime=path.stat().st_mtime,
        total=int(vulns.get("total") or 0),
        by_severity=dict(vulns.get("by_severity") or {}),
        blocked=blocked,
        tester_message=str(guard.get("tester_message") or ""),
        hosts_scanned=int(hosts_scan.get("hosts_scanned") or len(vulns.get("hosts_summary") or [])),
    )


def list_runs() -> list[ScanRun]:
    if not SCANS_DIR.exists():
        return []
    runs: list[ScanRun] = []
    for entry in SCANS_DIR.iterdir():
        if entry.name.startswith("_") or entry.name.endswith(".json") or entry.name.endswith(".log"):
            continue
        run = parse_run_dir(entry)
        if run:
            runs.append(run)
    runs.sort(key=lambda r: r.mtime, reverse=True)
    return runs


def list_reports() -> list[dict[str, Any]]:
    if not REPORTS_DIR.exists():
        return []
    items = []
    for p in REPORTS_DIR.glob("*.html"):
        items.append(
            {
                "name": p.name,
                "path": str(p),
                "mtime": p.stat().st_mtime,
                "size": p.stat().st_size,
            }
        )
    for p in sorted(REPORTS_DIR.glob("ai_*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        items.append(
            {
                "name": p.name,
                "path": str(p),
                "mtime": p.stat().st_mtime,
                "size": p.stat().st_size,
                "kind": "ai",
            }
        )
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def load_run_detail(run_id: str) -> dict[str, Any] | None:
    path = SCANS_DIR / run_id
    if not path.is_dir():
        return None
    run = parse_run_dir(path)
    if not run:
        return None

    vulns = _read_json(path / "vulnerabilities.json") or {}
    guard = _read_json(path / "guard_state.json") or {}
    hosts_scan = _read_json(path / "hosts_scan.json") or {}
    light = _read_json(path / "light.json") or {}
    deep = _read_json(path / "deep.json") or {}

    ai_pre = REPORTS_DIR / "ai_pre_scan.md"
    ai_post = REPORTS_DIR / "ai_post_scan.md"
    ai_pre_text = ai_pre.read_text(encoding="utf-8") if ai_pre.exists() else ""
    ai_post_text = ai_post.read_text(encoding="utf-8") if ai_post.exists() else ""

    related_reports = [p.name for p in related_report_paths(run)]

    scope_data: dict[str, Any] = {}
    scope_path = path / "scope.json"
    if scope_path.exists():
        raw_scope = _read_json(scope_path)
        if isinstance(raw_scope, dict):
            scope_data = raw_scope
    scope_rejected: list[str] = []
    rejected_path = path / "scope_rejected.json"
    if rejected_path.exists():
        rej = _read_json(rejected_path)
        if isinstance(rej, dict):
            scope_rejected = list(rej.get("rejected") or [])

    return {
        "run": run,
        "scope": scope_data,
        "scope_rejected": scope_rejected,
        "vulnerabilities": vulns,
        "guard": guard,
        "hosts_scan": hosts_scan,
        "light": light,
        "deep": deep,
        "items": vulns.get("items") or [],
        "hosts_summary": vulns.get("hosts_summary") or hosts_scan.get("hosts") or [],
        "recommended_actions": vulns.get("recommended_actions") or guard.get("recommendations") or [],
        "by_category": vulns.get("by_category") or {},
        "ai_pre_scan": ai_pre_text,
        "ai_post_scan": ai_post_text,
        "related_reports": related_reports[:10],
        "artifacts": sorted(
            [f.name for f in path.iterdir() if f.is_file() and not f.name.startswith(".")]
        ),
    }


def dashboard_stats(runs: list[ScanRun]) -> dict[str, Any]:
    domains = sorted({r.domain for r in runs})
    blocked = sum(1 for r in runs if r.blocked)
    total_findings = sum(r.total for r in runs)
    return {
        "run_count": len(runs),
        "domain_count": len(domains),
        "domains": domains,
        "blocked_count": blocked,
        "total_findings": total_findings,
    }
