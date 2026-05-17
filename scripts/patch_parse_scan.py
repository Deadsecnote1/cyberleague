#!/usr/bin/env python3
"""Fix Parse Scan Result to read last JSON line; merge guard/block into scan object."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"

PARSE_SCAN_JS = r"""
const raw = $input.first().json.stdout || '';
let scan;
try {
  const lines = raw.trim().split('\n').filter((l) => l.trim());
  const jsonLine = lines.length ? lines[lines.length - 1] : raw;
  scan = JSON.parse(jsonLine);
} catch (e) {
  scan = { ok: false, domain: $json.domain, error: e.message, raw: raw.slice(0, 1000) };
}

// Load vulnerabilities from workdir if missing on stdout payload
const fs = require('fs');
if (scan.workdir) {
  const vulnPath = `${scan.workdir}/vulnerabilities.json`;
  if (fs.existsSync(vulnPath)) {
    try {
      const fileV = JSON.parse(fs.readFileSync(vulnPath, 'utf8'));
      if (!scan.vulnerabilities?.items?.length && fileV.items?.length) {
        scan.vulnerabilities = fileV;
      }
    } catch (err) {}
  }
  const guardPath = `${scan.workdir}/guard_state.json`;
  if (fs.existsSync(guardPath)) {
    try {
      scan.guard = JSON.parse(fs.readFileSync(guardPath, 'utf8'));
    } catch (err) {}
  }
}

return [{ json: { ...$json, scan } }];
""".strip()


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    for n in nodes:
        if n["name"] == "Parse Scan Result":
            n["parameters"]["jsCode"] = PARSE_SCAN_JS
    conn.execute(
        'UPDATE workflow_entity SET nodes=?, updatedAt=datetime("now"), versionCounter=versionCounter+1 WHERE id=?',
        (json.dumps(nodes), wf_id),
    )
    conn.commit()
    print("Patched Parse Scan Result (last JSON line + workdir vuln fallback).")


if __name__ == "__main__":
    main()
