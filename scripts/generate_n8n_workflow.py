#!/usr/bin/env python3
"""Generate n8n workflow JSON for bug bounty pentest pipeline."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "n8n" / "bug-bounty-pentest-pipeline.json"


def nid() -> str:
    return str(uuid.uuid4())


def node(name: str, ntype: str, x: int, y: int, parameters: dict, **extra) -> dict:
    payload = {
        "parameters": parameters,
        "id": nid(),
        "name": name,
        "type": ntype,
        "typeVersion": extra.pop("typeVersion", 1),
        "position": [x, y],
    }
    payload.update(extra)
    return payload


def main() -> None:
    manual = node(
        "Start Scan",
        "n8n-nodes-base.manualTrigger",
        -640,
        0,
        {},
        typeVersion=1,
    )
    load_targets = node(
        "Load Targets (CSV)",
        "n8n-nodes-base.executeCommand",
        -400,
        0,
        {
            "command": "python3 /home/thanushiyan/Desktop/buildathon_cursor/scripts/fetch_bugcrowd_targets.py",
        },
        typeVersion=1,
    )
    parse_targets = node(
        "Parse Target List",
        "n8n-nodes-base.code",
        -160,
        0,
        {
            "jsCode": """
const raw = $input.first().json.stdout || '';
let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  throw new Error('Failed to parse targets JSON: ' + e.message + '\\n' + raw.slice(0, 500));
}
if (!payload.ok) {
  throw new Error(payload.error || 'Target loader failed');
}
if (!payload.targets?.length) {
  throw new Error('No in-scope targets in data/targets.csv. Add authorized Bugcrowd domains first.');
}
return payload.targets.map((t) => ({ json: t }));
""".strip()
        },
        typeVersion=2,
    )
    loop_batches = node(
        "Loop Targets",
        "n8n-nodes-base.splitInBatches",
        80,
        0,
        {"batchSize": 1, "options": {}},
        typeVersion=3,
    )
    run_scan = node(
        "Run Pentest Tools",
        "n8n-nodes-base.executeCommand",
        320,
        0,
        {
            "command": "=bash /home/thanushiyan/Desktop/buildathon_cursor/scripts/bugbounty-scan.sh {{ $json.domain }}"
        },
        typeVersion=1,
    )
    parse_scan = node(
        "Parse Scan Result",
        "n8n-nodes-base.code",
        560,
        0,
        {
            "jsCode": """
const raw = $input.first().json.stdout || '';
let scan;
try {
  scan = JSON.parse(raw);
} catch (e) {
  scan = { ok: false, domain: $json.domain, error: e.message, raw: raw.slice(0, 1000) };
}
return [{ json: { ...$json, scan } }];
""".strip()
        },
        typeVersion=2,
    )
    continue_loop = node(
        "Continue Loop",
        "n8n-nodes-base.noOp",
        800,
        120,
        {},
        typeVersion=1,
    )
    build_report = node(
        "Build HTML Report",
        "n8n-nodes-base.code",
        800,
        -120,
        {
            "jsCode": """
const items = $input.all();
const generatedAt = new Date().toISOString();
const rows = items.map((item) => {
  const s = item.json.scan || {};
  return {
    program: item.json.program,
    domain: item.json.domain,
    scope_raw: item.json.scope_raw,
    notes: item.json.notes,
    subdomain_count: s.subdomain_count ?? 0,
    ffuf_findings: s.ffuf_findings ?? 0,
    header_issues: (s.header_issues || []).join(', '),
    tools_missing: (s.tools_missing || []).join(', '),
    workdir: s.workdir || '',
    ok: s.ok !== false,
  };
});

const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Bug Bounty Scan Report</title>
<style>body{font-family:system-ui,sans-serif;margin:2rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:8px;text-align:left}th{background:#f5f5f5}.warn{color:#b45309}</style></head><body>`;
html += `<h1>Bug Bounty Pentest Report</h1><p>Generated: ${esc(generatedAt)}</p>`;
html += `<p class="warn">Only test domains you are authorized to assess under Bugcrowd program rules.</p>`;
html += '<table><tr><th>Program</th><th>Domain</th><th>Subdomains</th><th>FFUF hits</th><th>Header issues</th><th>Artifacts</th></tr>';
for (const r of rows) {
  html += `<tr><td>${esc(r.program)}</td><td>${esc(r.domain)}</td><td>${esc(r.subdomain_count)}</td><td>${esc(r.ffuf_findings)}</td><td>${esc(r.header_issues)}</td><td>${esc(r.workdir)}</td></tr>`;
}
html += '</table></body></html>';

const stamp = generatedAt.replace(/[:.]/g, '-');
const reportPath = `/home/thanushiyan/Desktop/buildathon_cursor/reports/bugbounty-report-${stamp}.html`;
return [{ json: { reportPath, html, summary: rows } }];
""".strip()
        },
        typeVersion=2,
    )
    save_report = node(
        "Save Report File",
        "n8n-nodes-base.executeCommand",
        1040,
        -120,
        {
            "command": "=echo '{{ JSON.stringify({ reportPath: $json.reportPath, html: $json.html }) }}' | python3 /home/thanushiyan/Desktop/buildathon_cursor/scripts/write_report.py"
        },
        typeVersion=1,
    )

    nodes = [
        manual,
        load_targets,
        parse_targets,
        loop_batches,
        run_scan,
        parse_scan,
        continue_loop,
        build_report,
        save_report,
    ]

    connections = {
        "Start Scan": {"main": [[{"node": "Load Targets (CSV)", "type": "main", "index": 0}]]},
        "Load Targets (CSV)": {"main": [[{"node": "Parse Target List", "type": "main", "index": 0}]]},
        "Parse Target List": {"main": [[{"node": "Loop Targets", "type": "main", "index": 0}]]},
        "Loop Targets": {
            "main": [
                [{"node": "Build HTML Report", "type": "main", "index": 0}],
                [
                    {"node": "Run Pentest Tools", "type": "main", "index": 0},
                    {"node": "Continue Loop", "type": "main", "index": 0},
                ],
            ]
        },
        "Run Pentest Tools": {"main": [[{"node": "Parse Scan Result", "type": "main", "index": 0}]]},
        "Parse Scan Result": {"main": [[{"node": "Loop Targets", "type": "main", "index": 0}]]},
        "Continue Loop": {"main": [[{"node": "Loop Targets", "type": "main", "index": 0}]]},
        "Build HTML Report": {"main": [[{"node": "Save Report File", "type": "main", "index": 0}]]},
    }

    workflow = [
        {
            "name": "Bug Bounty Pentest Pipeline",
            "nodes": nodes,
            "connections": connections,
            "settings": {"executionOrder": "v1"},
            "active": False,
        }
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(workflow, indent=2))
    print(OUT)


if __name__ == "__main__":
    main()
