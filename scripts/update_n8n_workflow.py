#!/usr/bin/env python3
"""Patch the Bug Bounty Pentest Pipeline workflow in n8n SQLite DB."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"

SCAN_CMD = (
    f"SCAN_PROFILE=both WORDLIST={ROOT}/wordlists/ffuf-quick.txt "
    f"FFUF_MAXTIME=90 NUCLEI_TIMEOUT=90 bash {ROOT}/scripts/bugbounty-scan.sh"
)

BUILD_REPORT_JS = (r"""
const items = $input.all().filter((item) => item.json.domain && item.json.scan);
const generatedAt = new Date().toISOString();
const rows = items.map((item) => {
  const s = item.json.scan || {};
  const light = s.light || {};
  const deep = s.deep || {};
  return {
    program: item.json.program,
    domain: item.json.domain,
    scan_profile: s.scan_profile || 'both',
    light_ffuf: light.ffuf_findings ?? 0,
    light_headers: (light.header_issues || []).join(', '),
    deep_nmap_ports: deep.nmap_findings ?? 0,
    deep_nuclei: deep.nuclei_findings ?? 0,
    tools_missing: (s.tools_missing || []).join(', '),
    workdir: s.workdir || '',
  };
});

const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Bug Bounty Scan Report</title>
<style>body{font-family:system-ui,sans-serif;margin:2rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:8px;text-align:left}th{background:#f5f5f5}.warn{color:#b45309}</style></head><body>`;
html += `<h1>Intentionally Vulnerable Targets — Scan Report</h1><p>Generated: ${esc(generatedAt)}</p>`;
html += `<p class="warn">Light path: subfinder, httpx, ffuf, headers. Deep path: nmap, nuclei. Only scan authorized/demo targets.</p>`;
html += '<table><tr><th>Program</th><th>Domain</th><th>Light FFUF</th><th>Header issues</th><th>Nmap open</th><th>Nuclei</th><th>Artifacts</th></tr>';
for (const r of rows) {
  html += `<tr><td>${esc(r.program)}</td><td>${esc(r.domain)}</td><td>${esc(r.light_ffuf)}</td><td>${esc(r.light_headers)}</td><td>${esc(r.deep_nmap_ports)}</td><td>${esc(r.deep_nuclei)}</td><td>${esc(r.workdir)}</td></tr>`;
}
html += '</table></body></html>';

const ROOT = '__ROOT__';
const stamp = generatedAt.replace(/[:.]/g, '-');
const reportPath = `${ROOT}/reports/bugbounty-report-${stamp}.html`;
const fs = require('fs');
fs.mkdirSync(`${ROOT}/reports`, { recursive: true });
fs.writeFileSync(reportPath, html, 'utf8');
return [{ json: { reportPath, summary: rows } }];
""".strip().replace("__ROOT__", ROOT))

PARSE_TARGETS_JS = r"""
const raw = $input.first().json.stdout || '';
let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  throw new Error('Failed to parse targets JSON: ' + e.message);
}
if (!payload.ok) throw new Error(payload.error || 'Target loader failed');
if (!payload.targets?.length) {
  throw new Error('No targets in data/targets.csv');
}
return payload.targets.map((t) => ({ json: t }));
""".strip()


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])

    for node in nodes:
        name = node.get("name", "")
        if name == "Load Targets (CSV)":
            node["name"] = "Load Vulnerable Targets"
            node["parameters"]["command"] = f"python3 {ROOT}/scripts/fetch_bugcrowd_targets.py"
        if name == "Run Pentest Tools":
            node["parameters"]["command"] = (
                f"=SCAN_PROFILE=both WORDLIST={ROOT}/wordlists/ffuf-quick.txt "
                f"FFUF_MAXTIME=90 NUCLEI_TIMEOUT=90 bash {ROOT}/scripts/bugbounty-scan.sh "
                "{{ $json.domain }}"
            )
        if name == "Parse Target List":
            node["parameters"]["jsCode"] = PARSE_TARGETS_JS
        if name == "Build HTML Report":
            node["parameters"]["jsCode"] = BUILD_REPORT_JS
        if name == "Save Report File":
            node["parameters"] = {
                "jsCode": "return [{ json: { reportPath: $json.reportPath, message: 'Report saved' } }];"
            }
            node["type"] = "n8n-nodes-base.code"
            node["typeVersion"] = 2

    conn.execute(
        'UPDATE workflow_entity SET nodes=?, updatedAt=datetime("now"), versionCounter=versionCounter+1 WHERE id=?',
        (json.dumps(nodes), wf_id),
    )
    conn.commit()
    print("updated", wf_id)


if __name__ == "__main__":
    main()
