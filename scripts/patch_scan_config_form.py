#!/usr/bin/env python3
"""Add tester configuration fields to n8n form triggers."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"

CONFIG_FIELDS = [
    {
        "fieldLabel": "Program name (optional)",
        "fieldType": "text",
        "requiredField": False,
        "placeholder": "e.g. myownsite",
    },
    {
        "fieldLabel": "Max subdomain hosts",
        "fieldType": "number",
        "requiredField": True,
        "defaultValue": 5,
    },
    {
        "fieldLabel": "FFUF per host",
        "fieldType": "dropdown",
        "requiredField": True,
        "fieldOptions": {
            "values": [
                {"option": "Yes"},
                {"option": "No"},
            ]
        },
        "defaultValue": "No",
    },
    {
        "fieldLabel": "Nuclei per host",
        "fieldType": "dropdown",
        "requiredField": True,
        "fieldOptions": {
            "values": [
                {"option": "Yes"},
                {"option": "No"},
            ]
        },
        "defaultValue": "No",
    },
    {
        "fieldLabel": "Scan all subdomains",
        "fieldType": "dropdown",
        "requiredField": True,
        "fieldOptions": {
            "values": [
                {"option": "Yes"},
                {"option": "No"},
            ]
        },
        "defaultValue": "Yes",
    },
    {
        "fieldLabel": "Scan profile",
        "fieldType": "dropdown",
        "requiredField": True,
        "fieldOptions": {
            "values": [
                {"option": "light"},
                {"option": "deep"},
                {"option": "both"},
            ]
        },
        "defaultValue": "light",
    },
    {
        "fieldLabel": "Request delay (ms)",
        "fieldType": "number",
        "requiredField": True,
        "defaultValue": 500,
    },
    {
        "fieldLabel": "Max requests per minute",
        "fieldType": "number",
        "requiredField": True,
        "defaultValue": 30,
    },
]

PARSE_MANUAL_URL_JS = r"""
const form = $input.first().json;

function field(form, ...keys) {
  for (const k of keys) {
    if (form[k] !== undefined && form[k] !== null && String(form[k]).trim() !== '') {
      return form[k];
    }
  }
  return '';
}

function yesNo(val, defaultYes = true) {
  const s = String(val ?? '').trim().toLowerCase();
  if (!s) return defaultYes;
  if (s === 'no' || s === 'n' || s === 'false' || s === '0') return false;
  return true;
}

const url = field(form, 'Target URL', 'Target URL:');
const program = field(form, 'Program name (optional)', 'Program name') || 'Manual URL entry';

const raw = String(url).trim();
if (!raw) throw new Error('Target URL is required.');

let domain = raw
  .replace(/^https?:\/\//i, '')
  .replace(/^www\./i, '')
  .split('/')[0]
  .split(':')[0]
  .toLowerCase();

if (!domain || !domain.includes('.')) {
  throw new Error('Enter a valid URL or domain.');
}

const scan_config = {
  max_hosts: Number(field(form, 'Max subdomain hosts') || 5),
  ffuf_per_host: yesNo(field(form, 'FFUF per host'), false),
  nuclei_per_host: yesNo(field(form, 'Nuclei per host'), false),
  scan_all_subdomains: yesNo(field(form, 'Scan all subdomains'), true),
  profile: String(field(form, 'Scan profile') || 'light').toLowerCase(),
  request_delay_ms: Number(field(form, 'Request delay (ms)') || 500),
  requests_per_minute: Number(field(form, 'Max requests per minute') || 30),
};

const fs = require('fs');
const domainFile = '/home/thanushiyan/Desktop/buildathon_cursor/.current_scan_domain';
try { fs.writeFileSync(domainFile, domain, 'utf8'); } catch (e) {}

return [{
  json: {
    program: String(program).trim(),
    domain,
    scope_raw: raw,
    notes: 'Entered via form',
    source: 'manual_url',
    scan_config,
  },
}];
""".strip()

PARSE_TARGET_LIST_JS = r"""
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

let form = {};
try {
  form = $('Scan from CSV (form)').first().json;
} catch (e) {
  form = {};
}

function field(form, ...keys) {
  for (const k of keys) {
    if (form[k] !== undefined && form[k] !== null && String(form[k]).trim() !== '') {
      return form[k];
    }
  }
  return '';
}

function yesNo(val, defaultYes = true) {
  const s = String(val ?? '').trim().toLowerCase();
  if (!s) return defaultYes;
  return s === 'yes' || s === 'y' || s === 'true' || s === '1';
}

const scan_config = {
  max_hosts: Number(field(form, 'Max subdomain hosts') || 5),
  ffuf_per_host: yesNo(field(form, 'FFUF per host'), false),
  nuclei_per_host: yesNo(field(form, 'Nuclei per host'), false),
  scan_all_subdomains: yesNo(field(form, 'Scan all subdomains'), true),
  profile: String(field(form, 'Scan profile') || 'light').toLowerCase(),
  request_delay_ms: Number(field(form, 'Request delay (ms)') || 500),
  requests_per_minute: Number(field(form, 'Max requests per minute') || 30),
};

return payload.targets.map((t) => ({
  json: {
    ...t,
    scan_config,
    program: field(form, 'Program name (optional)') || t.program,
  },
}));
""".strip()

DOMAIN_FILE = f"{ROOT}/.current_scan_domain"
RUN_SCAN_CMD = (
    f"=SCAN_PROFILE={{{{ ($json.scan_config || {{}}).profile || 'light' }}}} "
    f"SCAN_ALL_SUBDOMAINS={{{{ ($json.scan_config || {{}}).scan_all_subdomains === false ? '0' : '1' }}}} "
    f"MAX_SUBDOMAIN_SCANS={{{{ ($json.scan_config || {{}}).max_hosts || 5 }}}} "
    f"SCAN_MAX_RUNTIME_MINUTES={{{{ ($json.scan_config || {{}}).max_runtime_minutes || 0 }}}} "
    f"FFUF_PER_HOST={{{{ ($json.scan_config || {{}}).ffuf_per_host === false ? '0' : '1' }}}} "
    f"NUCLEI_PER_HOST={{{{ ($json.scan_config || {{}}).nuclei_per_host === false ? '0' : '1' }}}} "
    f"SQLI_SCAN={{{{ ($json.scan_config || {{}}).sqli_scan === false ? '0' : '1' }}}} "
    f"REQUEST_DELAY_MS={{{{ ($json.scan_config || {{}}).request_delay_ms || 500 }}}} "
    f"REQUESTS_PER_MINUTE={{{{ ($json.scan_config || {{}}).requests_per_minute || 30 }}}} "
    f"WORDLIST={ROOT}/wordlists/ffuf-quick.txt FFUF_MAXTIME=60 PER_HOST_NUCLEI_TIMEOUT=60 "
    f"NUCLEI_TIMEOUT=180 NIKTO_TIMEOUT=90 "
    f"bash {ROOT}/scripts/bugbounty-scan.sh $(cat {DOMAIN_FILE} 2>/dev/null || echo invalid)"
)


def form_params(title: str, description: str, url_field: bool, webhook_id: str) -> dict:
    fields = []
    if url_field:
        fields.append(
            {
                "fieldLabel": "Target URL",
                "fieldType": "text",
                "requiredField": True,
                "placeholder": "https://example.com",
            }
        )
    fields.extend(CONFIG_FIELDS)
    return {
        "path": webhook_id,
        "formTitle": title,
        "formDescription": description,
        "formFields": {"values": fields},
        "options": {},
    }


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    connections = json.loads(
        conn.execute("SELECT connections FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0]
    )

    csv_webhook = str(uuid.uuid4())

    for node in nodes:
        name = node.get("name", "")
        if name == "Enter Target URL":
            node["name"] = "Pentest Scan (single URL)"
            node["parameters"] = form_params(
                "Pentest Scan — Single URL",
                "Enter target URL and scan options. Only test authorized targets.",
                url_field=True,
                webhook_id=node.get("webhookId") or str(uuid.uuid4()),
            )
            if not node.get("webhookId"):
                node["webhookId"] = node["parameters"]["path"]

        if name == "Scan from CSV":
            node["name"] = "Scan from CSV (form)"
            node["type"] = "n8n-nodes-base.formTrigger"
            node["typeVersion"] = 2.2
            node["parameters"] = form_params(
                "Pentest Scan — targets.csv",
                "Load all targets from data/targets.csv with your chosen scan options.",
                url_field=False,
                webhook_id=csv_webhook,
            )
            node["webhookId"] = csv_webhook
            node.pop("disabled", None)

        if name == "Parse Manual URL":
            node["parameters"]["jsCode"] = PARSE_MANUAL_URL_JS

        if name == "Parse Target List":
            node["parameters"]["jsCode"] = PARSE_TARGET_LIST_JS

        if name == "Run Pentest Tools":
            node["parameters"]["command"] = RUN_SCAN_CMD

    # Fix connection key rename
    if "Scan from CSV" in connections:
        connections["Scan from CSV (form)"] = connections.pop("Scan from CSV")
    if "Enter Target URL" in connections:
        connections["Pentest Scan (single URL)"] = connections.pop("Enter Target URL")

    conn.execute(
        """UPDATE workflow_entity
           SET nodes=?, connections=?, updatedAt=datetime('now'), versionCounter=versionCounter+1
           WHERE id=?""",
        (json.dumps(nodes), json.dumps(connections), wf_id),
    )
    conn.commit()

    print("Patched forms:")
    print("  - Pentest Scan (single URL)")
    print("  - Scan from CSV (form)")
    for n in nodes:
        if n.get("type", "").endswith("formTrigger"):
            wid = n.get("webhookId") or n.get("parameters", {}).get("path", "")
            print(f"  Form URL: http://localhost:5678/form/{wid}")


if __name__ == "__main__":
    main()
