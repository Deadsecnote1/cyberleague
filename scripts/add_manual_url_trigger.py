#!/usr/bin/env python3
"""Add Form Trigger + manual URL parsing path to the pentest workflow."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

WF_ID_FILE = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"

PARSE_MANUAL_URL_JS = r"""
const form = $input.first().json;
const url =
  form['Target URL'] ||
  form['Target URL:'] ||
  form['target_url'] ||
  form.targetUrl ||
  '';
const program =
  form['Program name (optional)'] ||
  form['Program name'] ||
  form.program ||
  'Manual URL entry';

const raw = String(url).trim();
if (!raw) {
  throw new Error('Target URL is required.');
}

let domain = raw
  .replace(/^https?:\/\//i, '')
  .replace(/^www\./i, '')
  .split('/')[0]
  .split(':')[0]
  .toLowerCase();

if (!domain || !domain.includes('.')) {
  throw new Error('Enter a valid URL or domain, e.g. https://demo.testfire.net');
}

return [{
  json: {
    program: String(program).trim() || 'Manual URL entry',
    domain,
    scope_raw: raw,
    notes: 'Entered via form',
    source: 'manual_url',
  },
}];
""".strip()


def main() -> None:
    wf_id = WF_ID_FILE.read_text().strip()
    conn = sqlite3.connect(DB)
    row = conn.execute(
        "SELECT nodes, connections FROM workflow_entity WHERE id=?", (wf_id,)
    ).fetchone()
    nodes = json.loads(row[0])
    connections = json.loads(row[1])

    if any(n.get("name") == "Enter Target URL" for n in nodes):
        print("Form trigger already present")
        return

    webhook_id = str(uuid.uuid4())
    form_node = {
        "parameters": {
            "path": webhook_id,
            "formTitle": "Bug Bounty — Scan a single URL",
            "formDescription": "Enter one target URL or domain. Only scan sites you are authorized to test.",
            "formFields": {
                "values": [
                    {
                        "fieldLabel": "Target URL",
                        "fieldType": "text",
                        "requiredField": True,
                        "placeholder": "https://demo.testfire.net",
                    },
                    {
                        "fieldLabel": "Program name (optional)",
                        "fieldType": "text",
                        "requiredField": False,
                        "placeholder": "My program name",
                    },
                ]
            },
            "options": {},
        },
        "id": str(uuid.uuid4()),
        "name": "Enter Target URL",
        "type": "n8n-nodes-base.formTrigger",
        "typeVersion": 2.2,
        "position": [-640, 48],
        "webhookId": webhook_id,
    }

    parse_manual = {
        "parameters": {"jsCode": PARSE_MANUAL_URL_JS},
        "id": str(uuid.uuid4()),
        "name": "Parse Manual URL",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-192, 48],
    }

    for node in nodes:
        if node.get("name") == "Start Scan":
            node["name"] = "Scan from CSV"
        if node.get("name") == "Loop Targets":
            node["parameters"] = {"batchSize": 1, "options": {}}

    nodes.extend([form_node, parse_manual])

    connections["Enter Target URL"] = {
        "main": [[{"node": "Parse Manual URL", "type": "main", "index": 0}]]
    }
    connections["Parse Manual URL"] = {
        "main": [[{"node": "Loop Targets", "type": "main", "index": 0}]]
    }

    trigger_count = sum(
        1
        for n in nodes
        if n.get("type", "").endswith("Trigger") or "trigger" in n.get("type", "").lower()
    )

    conn.execute(
        """UPDATE workflow_entity
           SET nodes=?, connections=?, updatedAt=datetime('now'),
               versionCounter=versionCounter+1, triggerCount=?
           WHERE id=?""",
        (json.dumps(nodes), json.dumps(connections), trigger_count, wf_id),
    )
    conn.commit()
    print("Added Enter Target URL form trigger ->", wf_id)
    print("Form test URL: http://localhost:5678/form/" + webhook_id)


if __name__ == "__main__":
    main()
