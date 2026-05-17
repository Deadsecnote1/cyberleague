#!/usr/bin/env python3
"""Add OpenAI advisor nodes to the pentest n8n workflow."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"
SCRIPTS = Path(__file__).resolve().parent

PREPARE_AI_CONTEXT_JS = r"""
function aiEnabled() {
  const build = $input.first().json;
  if (build.portal_meta && build.portal_meta.enable_ai === false) return false;
  const forms = ['Pentest Scan (single URL)', 'Scan from CSV (form)'];
  for (const name of forms) {
    try {
      const f = $(name).first().json;
      const v = String(f['Enable AI hunt advisor'] || 'Yes').toLowerCase();
      if (v === 'no' || v === 'false' || v === '0') return false;
      return true;
    } catch (e) {}
  }
  return true;
}

const build = $input.first().json;
const bundle = build.summary || [];
const bundlePath = `/tmp/n8n-ai-bundle-${Date.now()}.json`;
const enabled = aiEnabled();

return [{
  json: {
    ai_enabled: enabled,
    ai_skipped: !enabled,
    workdir: build.primary_workdir || '',
    reportPath: build.reportPath,
    html: build.html,
    bundle_path: bundlePath,
    bundle,
  },
}];
""".strip()

WRITE_AI_BUNDLE_JS = r"""
const fs = require('fs');
if ($json.ai_skipped) {
  return [{ json: { ...$json } }];
}
fs.writeFileSync($json.bundle_path, JSON.stringify($json.bundle, null, 2));
return [{ json: { ...$json, bundle_written: true } }];
""".strip()

PARSE_AI_JS = r"""
if ($json.ai_skipped) {
  return [{
    json: {
      ai_skipped: true,
      ai_markdown: '',
      reportPath: $json.reportPath,
      html: $json.html,
    },
  }];
}
const raw = $input.first().json.stdout || '';
let out;
try { out = JSON.parse(raw); } catch (e) { out = { ok: false, error: e.message }; }
let md = '';
if (out.markdown_path) {
  try { md = require('fs').readFileSync(out.markdown_path, 'utf8'); } catch (e) { md = ''; }
}
const prep = $('Prepare AI Context').first().json;
return [{
  json: {
    ai_ok: out.ok !== false,
    ai_markdown: md,
    reportPath: prep.reportPath,
    html: prep.html,
  },
}];
""".strip()

MERGE_AI_REPORT_JS = r"""
const ai = $input.first().json;
let html = ai.html || '';
if (ai.ai_markdown && !ai.ai_skipped) {
  const esc = (t) => String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  html = html.replace('</body></html>', '');
  html += '<h2>AI Hunt Advisor (OpenAI)</h2>';
  html += '<pre style="white-space:pre-wrap;font-family:system-ui,sans-serif;background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0">';
  html += esc(ai.ai_markdown);
  html += '</pre></body></html>';
}
const reportPath = ai.reportPath || '';
if (reportPath) require('fs').writeFileSync(reportPath, html, 'utf8');
return [{ json: { reportPath, html, ai_merged: !ai.ai_skipped } }];
""".strip()

PRE_SCAN_PREPARE_JS = r"""
function aiEnabled() {
  const item = $input.first().json;
  if (item.portal_meta && item.portal_meta.enable_ai === false) return false;
  if (item.portal_meta && item.portal_meta.enable_ai === true) return true;
  const forms = ['Pentest Scan (single URL)', 'Scan from CSV (form)'];
  for (const name of forms) {
    try {
      const f = $(name).first().json;
      const v = String(f['Enable AI hunt advisor'] || 'Yes').toLowerCase();
      if (v === 'no' || v === 'false' || v === '0') return false;
      return true;
    } catch (e) {}
  }
  return true;
}

const enabled = aiEnabled();
const targets = $input.all().map((item) => item.json);
if (!enabled) {
  return targets.map((t) => ({ json: { ...t, ai_pre_skipped: true } }));
}

const fs = require('fs');
const prePath = `/tmp/n8n-pre-scan-${Date.now()}.json`;
fs.writeFileSync(prePath, JSON.stringify(targets, null, 2));
return targets.map((t) => ({ json: { ...t, ai_pre_path: prePath, ai_pre_skipped: false } }));
""".strip()

AI_CMD = (
    f"=if [ \"{{{{ $json.ai_skipped }}}}\" = \"true\" ]; then "
    f"echo '{{\"ok\":true,\"ai_skipped\":true}}'; else "
    f"OPENAI_API_KEY=$(grep -E '^OPENAI_API_KEY=' {ROOT}/config/openai.env 2>/dev/null | cut -d= -f2- | tr -d '\"'); "
    f"export OPENAI_API_KEY; "
    f"python3 {ROOT}/scripts/ai_pentest_advisor.py --phase post_scan "
    f"--bundle \"{{{{ $json.bundle_path }}}}\" --out-dir {ROOT}/reports "
    f"|| echo '{{\"ok\":true,\"ai_skipped\":true,\"error\":\"ai_failed\"}}'; fi"
)

PRE_SCAN_CMD = (
    f"=if [ \"{{{{ $json.ai_pre_skipped }}}}\" = \"true\" ]; then "
    f"echo '{{\"ok\":true,\"ai_pre_skipped\":true}}'; else "
    f"OPENAI_API_KEY=$(grep -E '^OPENAI_API_KEY=' {ROOT}/config/openai.env 2>/dev/null | cut -d= -f2- | tr -d '\"'); "
    f"export OPENAI_API_KEY; "
    f"python3 {ROOT}/scripts/ai_pentest_advisor.py --phase pre_scan "
    f"--targets-json \"{{{{ $json.ai_pre_path }}}}\" --out-dir {ROOT}/reports "
    f"|| echo '{{\"ok\":true,\"ai_pre_skipped\":true,\"error\":\"ai_failed\"}}'; fi"
)

def exec_params(cmd: str) -> dict:
    return {"command": cmd, "options": {"continueOnFail": True}}


RESTORE_SCAN_TARGETS_JS = r"""
// Execute Command replaces $json with stdout; restore target rows for the loop.
return $('AI Pre-Scan Prepare').all().map((item) => ({ json: { ...item.json } }));
""".strip()


AI_NODES = {
    "AI Pre-Scan Prepare": ("n8n-nodes-base.code", {"jsCode": PRE_SCAN_PREPARE_JS}, 2),
    "AI Pre-Scan (OpenAI)": ("n8n-nodes-base.executeCommand", exec_params(PRE_SCAN_CMD), 1),
    "Restore Scan Targets": ("n8n-nodes-base.code", {"jsCode": RESTORE_SCAN_TARGETS_JS}, 2),
    "Prepare AI Context": ("n8n-nodes-base.code", {"jsCode": PREPARE_AI_CONTEXT_JS}, 2),
    "Write AI Bundle": ("n8n-nodes-base.code", {"jsCode": WRITE_AI_BUNDLE_JS}, 2),
    "AI Hunt Advisor (OpenAI)": ("n8n-nodes-base.executeCommand", exec_params(AI_CMD), 1),
    "Parse AI Response": ("n8n-nodes-base.code", {"jsCode": PARSE_AI_JS}, 2),
    "Merge AI Into Report": ("n8n-nodes-base.code", {"jsCode": MERGE_AI_REPORT_JS}, 2),
}

AI_POSITIONS = {
    "AI Pre-Scan Prepare": [200, -120],
    "AI Pre-Scan (OpenAI)": [440, -120],
    "Restore Scan Targets": [560, -120],
    "Prepare AI Context": [1040, -280],
    "Write AI Bundle": [1280, -280],
    "AI Hunt Advisor (OpenAI)": [1520, -280],
    "Parse AI Response": [1760, -280],
    "Merge AI Into Report": [2000, -280],
}

AI_FIELD = {
    "fieldLabel": "Enable AI hunt advisor",
    "fieldType": "dropdown",
    "requiredField": True,
    "fieldOptions": {"values": [{"option": "Yes"}, {"option": "No"}]},
    "defaultValue": "Yes",
}


def nid() -> str:
    return str(uuid.uuid4())


def upsert_node(nodes: list, name: str, ntype: str, params: dict, version: int) -> None:
    for n in nodes:
        if n["name"] == name:
            n["parameters"] = params
            n["type"] = ntype
            n["typeVersion"] = version
            return
    x, y = AI_POSITIONS[name]
    nodes.append(
        {
            "parameters": params,
            "id": nid(),
            "name": name,
            "type": ntype,
            "typeVersion": version,
            "position": [x, y],
        }
    )


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    connections = json.loads(
        conn.execute("SELECT connections FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0]
    )

    for name, (ntype, params, ver) in AI_NODES.items():
        upsert_node(nodes, name, ntype, params, ver)

    connections["Parse Target List"] = {
        "main": [[{"node": "AI Pre-Scan Prepare", "type": "main", "index": 0}]]
    }
    connections["AI Pre-Scan Prepare"] = {
        "main": [[{"node": "AI Pre-Scan (OpenAI)", "type": "main", "index": 0}]]
    }
    connections["AI Pre-Scan (OpenAI)"] = {
        "main": [[{"node": "Restore Scan Targets", "type": "main", "index": 0}]]
    }
    connections["Restore Scan Targets"] = {
        "main": [[{"node": "Loop Targets", "type": "main", "index": 0}]]
    }
    connections["Parse Manual URL"] = {
        "main": [[{"node": "AI Pre-Scan Prepare", "type": "main", "index": 0}]]
    }
    connections["Build HTML Report"] = {
        "main": [[{"node": "Prepare AI Context", "type": "main", "index": 0}]]
    }
    connections["Prepare AI Context"] = {
        "main": [[{"node": "Write AI Bundle", "type": "main", "index": 0}]]
    }
    connections["Write AI Bundle"] = {
        "main": [[{"node": "AI Hunt Advisor (OpenAI)", "type": "main", "index": 0}]]
    }
    connections["AI Hunt Advisor (OpenAI)"] = {
        "main": [[{"node": "Parse AI Response", "type": "main", "index": 0}]]
    }
    connections["Parse AI Response"] = {
        "main": [[{"node": "Merge AI Into Report", "type": "main", "index": 0}]]
    }
    connections["Merge AI Into Report"] = {
        "main": [[{"node": "Save Report File", "type": "main", "index": 0}]]
    }

    for n in nodes:
        if n.get("type") == "n8n-nodes-base.formTrigger":
            fields = n["parameters"].setdefault("formFields", {}).setdefault("values", [])
            if not any(f.get("fieldLabel") == "Enable AI hunt advisor" for f in fields):
                fields.append(AI_FIELD)

    conn.execute(
        "UPDATE workflow_entity SET nodes=?, connections=?, updatedAt=datetime('now'), versionCounter=versionCounter+1 WHERE id=?",
        (json.dumps(nodes), json.dumps(connections), wf_id),
    )
    conn.commit()
    print("AI workflow patched.")
    print(f"  1. cp {ROOT}/config/openai.env.example {ROOT}/config/openai.env")
    print("  2. Add OPENAI_API_KEY=sk-...")
    print("  3. Refresh workflow in n8n (http://localhost:5678)")


if __name__ == "__main__":
    main()
