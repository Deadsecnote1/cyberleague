# Pentest scope

Cyber League enforces **program scope** so subdomain discovery does not automatically scan out-of-scope assets.

## Portal configuration

On **New scan** → **Pentest scope**:

| Field | Description |
|-------|-------------|
| **Scope mode** | `apex_only`, `subdomains` (default), or `custom` |
| **In-scope hosts** | One host or pattern per line (`example.com`, `*.example.com`) |
| **Out of scope** | Excluded hosts (e.g. `staging.example.com`) |
| **Scope notes** | Free text for reports / AI advisor |
| **Load scope template** | JSON files in `config/scopes/` |

Target URL must match in-scope rules or the portal **blocks** the scan.

## Scope modes

### Apex only

Only the exact host from the target URL (no wildcard subdomains).

### Root + subdomains (default)

Allows `root_domain` and `*.root_domain` minus exclusions.

### Custom

Only hosts/patterns listed in **In-scope hosts** (minus exclusions).

## Enforcement points

1. **Portal** — `validate_target_url()` before triggering n8n  
2. **Discovery** — `scope_utils.py filter-workdir` filters `subdomains.txt` and `hosts.txt`  
3. **Per-host scans** — `scan_subdomains.py` skips out-of-scope hosts  
4. **Artifacts** — `scans/<run>/scope.json`, optional `scope_rejected.json`  
5. **Run detail page** — shows scope and rejection count  

## Scope file format

Written to `scans/<run>/scope.json`:

```json
{
  "root_domain": "testphp.vulnweb.com",
  "mode": "subdomains",
  "in_scope": ["testphp.vulnweb.com", "*.testphp.vulnweb.com"],
  "out_of_scope": [],
  "notes": "Acunetix test site only",
  "program": "vulnweb-lab",
  "target_url": "http://testphp.vulnweb.com"
}
```

## Templates

Add JSON under `config/scopes/`:

```json
{
  "program": "My Program",
  "root_domain": "example.com",
  "mode": "subdomains",
  "in_scope": ["example.com", "*.example.com"],
  "out_of_scope": ["staging.example.com"],
  "notes": "Production assets only"
}
```

Examples shipped: `example-program.json`, `vulnweb-test.json`.

## CLI

```bash
python3 scripts/scope_utils.py filter-workdir scans/example.com_20260516T120000Z
```
