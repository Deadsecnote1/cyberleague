# n8n setup — Cyber League

## Prerequisites

- n8n installed (`n8n --version`)
- Linux host with project cloned
- Workflow ID in `portal/n8n_config.json` (default: `rhace4vJpP80gdoJ`)

## Required environment variables

n8n v2 disables **Execute Command** and restricts Code node `fs` by default. Start n8n with:

```bash
export NODES_EXCLUDE='[]'
export NODE_FUNCTION_ALLOW_BUILTIN='fs,path,os,crypto,util'
n8n start
```

`./cyberleague.sh` sets these for you.

## Import workflow

1. Open n8n → **Workflows** → **Import from file**
2. Select `n8n/bug-bounty-pentest-pipeline.json`
3. Note the new workflow ID; update `portal/n8n_config.json` if it differs:
   ```json
   {
     "base_url": "http://localhost:5678",
     "workflow_id": "YOUR_WORKFLOW_ID",
     "webhook_path": "portal-scan",
     "form_webhook_id": "YOUR_FORM_ID"
   }
   ```

## Apply patches (existing local n8n DB)

If you already have the workflow in `~/.n8n/database.sqlite` from development:

```bash
cd /path/to/cyberleague
python3 scripts/patch_all_workflow.py
python3 scripts/patch_portal_webhook.py
```

Then in n8n UI: open workflow → **Save** → toggle **Inactive** → **Active** (refreshes webhooks).

Sync history without overwriting run command incorrectly:

```bash
# Updates workflow_history from entity (safe sync — does not reset Run Pentest cmd to legacy)
python3 - <<'PY'
import json, sqlite3
from pathlib import Path
wf_id = Path(".workflow_id").read_text().strip()
db = Path.home() / ".n8n/database.sqlite"
conn = sqlite3.connect(db)
nodes, connections = conn.execute(
    "SELECT nodes, connections FROM workflow_entity WHERE id=?", (wf_id,)
).fetchone()
row = conn.execute(
    "SELECT versionId FROM workflow_history WHERE workflowId=? ORDER BY createdAt DESC LIMIT 1",
    (wf_id,),
).fetchone()
if row:
    conn.execute(
        "UPDATE workflow_history SET nodes=?, connections=? WHERE workflowId=? AND versionId=?",
        (nodes, connections, wf_id, row[0]),
    )
    conn.commit()
print("synced")
PY
```

## Activate workflow

1. Open **Bug Bounty Pentest Pipeline**
2. Toggle **Active** (top-right)
3. Confirm webhook: `http://localhost:5678/webhook/portal-scan`
4. Form URL (fallback): shown in n8n for **Pentest Scan (single URL)** trigger

## Verify

```bash
curl -s http://localhost:5678/healthz
curl -s http://127.0.0.1:8765/health
```

Portal **New scan** → submit → **Executions** in n8n should show a new run.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Webhook 404 | Workflow not Active; re-toggle Active after patches |
| `executeCommand` disabled | Set `NODES_EXCLUDE=[]`, restart n8n |
| `Module 'fs' is disallowed` | Set `NODE_FUNCTION_ALLOW_BUILTIN=fs,path,os,crypto,util` |
| Domain `undefined` in shell | Ensure `.current_scan_domain` written; use latest `patch_portal_webhook.py` |
| Portal cannot start scan | Check n8n logs `logs/n8n.log`; try form fallback |

## Manual scan (without portal)

```bash
export NODES_EXCLUDE='[]'
export NODE_FUNCTION_ALLOW_BUILTIN='fs,path,os,crypto,util'
echo "testphp.vulnweb.com" > .current_scan_domain
SCAN_PROFILE=light SQLI_SCAN=1 bash scripts/bugbounty-scan.sh
```
