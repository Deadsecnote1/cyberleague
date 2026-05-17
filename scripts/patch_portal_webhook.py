#!/usr/bin/env python3
"""Add Portal Scan webhook to n8n workflow — portal triggers engine via HTTP."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
WEBHOOK_PATH = "portal-scan"

PARSE_PORTAL_JS = r"""
const body = $json.body || $json;
const url = String(body.target_url || body.url || '').trim();
if (!url) throw new Error('target_url is required');

let domain = url
  .replace(/^https?:\/\//i, '')
  .replace(/^www\./i, '')
  .split('/')[0]
  .split(':')[0]
  .toLowerCase();

if (!domain || !domain.includes('.')) {
  throw new Error('Invalid target_url');
}

const c = body.scan_config || {};
const yn = (v, d = true) => (v === false || v === 'false' || v === 'no' ? false : d);

const scan_config = {
  max_hosts: Number(c.max_hosts || 5),
  ffuf_per_host: yn(c.ffuf_per_host, false),
  nuclei_per_host: yn(c.nuclei_per_host, false),
  scan_all_subdomains: yn(c.scan_all_subdomains, true),
  sqli_scan: yn(c.sqli_scan, true),
  profile: String(c.profile || 'light').toLowerCase(),
  request_delay_ms: Number(c.request_delay_ms || 500),
  requests_per_minute: Number(c.requests_per_minute || 30),
  max_runtime_minutes: Number(c.max_runtime_minutes || 0),
};

const scopeIn = body.scope || {};
const scope = {
  root_domain: domain,
  mode: String(scopeIn.mode || 'subdomains').toLowerCase(),
  in_scope: Array.isArray(scopeIn.in_scope) ? scopeIn.in_scope : [domain, '*.' + domain],
  out_of_scope: Array.isArray(scopeIn.out_of_scope) ? scopeIn.out_of_scope : [],
  notes: String(scopeIn.notes || '').trim(),
  program: String(body.program || scopeIn.program || 'portal').trim(),
  target_url: url,
};

const fs = require('fs');
const ROOT = '/home/thanushiyan/Desktop/buildathon_cursor';
try {
  fs.writeFileSync(ROOT + '/.current_scan_domain', domain, 'utf8');
  fs.writeFileSync(ROOT + '/.current_scan_scope.json', JSON.stringify(scope, null, 2), 'utf8');
} catch (e) {}

return [{
  json: {
    program: scope.program || 'portal',
    domain,
    scope_raw: url,
    scope,
    notes: scope.notes || 'Triggered from portal webhook',
    source: 'portal_webhook',
    scan_config,
    portal_meta: {
      enable_ai: body.enable_ai !== false,
      triggered_at: new Date().toISOString(),
    },
  },
}];
""".strip()


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    connections = json.loads(
        conn.execute("SELECT connections FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0]
    )

    if not any(n["name"] == "Portal Scan (webhook)" for n in nodes):
        wh_id = str(uuid.uuid4())
        nodes.append(
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": WEBHOOK_PATH,
                    "responseMode": "onReceived",
                    "options": {},
                },
                "disabled": False,
                "id": str(uuid.uuid4()),
                "name": "Portal Scan (webhook)",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [-200, -120],
                "webhookId": wh_id,
            }
        )
        nodes.append(
            {
                "parameters": {"jsCode": PARSE_PORTAL_JS},
                "id": str(uuid.uuid4()),
                "name": "Parse Portal Request",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [40, -120],
            }
        )

    for n in nodes:
        if n["name"] == "Parse Portal Request":
            n["parameters"]["jsCode"] = PARSE_PORTAL_JS
        if n["name"] == "Portal Scan (webhook)":
            n["parameters"]["path"] = WEBHOOK_PATH
            n["parameters"]["httpMethod"] = "POST"
            n["parameters"]["responseMode"] = "onReceived"
            n.pop("disabled", None)
            if not n.get("webhookId"):
                n["webhookId"] = str(uuid.uuid4())

    connections["Portal Scan (webhook)"] = {
        "main": [[{"node": "Parse Portal Request", "type": "main", "index": 0}]]
    }
    connections["Parse Portal Request"] = {
        "main": [[{"node": "AI Pre-Scan Prepare", "type": "main", "index": 0}]]
    }

    conn.execute(
        "UPDATE workflow_entity SET nodes=?, connections=?, updatedAt=datetime('now'), versionCounter=versionCounter+1 WHERE id=?",
        (json.dumps(nodes), json.dumps(connections), wf_id),
    )
    conn.commit()
    print("Portal webhook patched.")
    print("  URL (when workflow active): http://localhost:5678/webhook/portal-scan")
    print("  Republish/toggle Active in n8n if you get 404.")


if __name__ == "__main__":
    main()
