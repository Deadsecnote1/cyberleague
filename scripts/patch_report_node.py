#!/usr/bin/env python3
"""Update Build HTML Report — findings fallback, IP block banner, scan status."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"

BUILD_REPORT_JS = (r"""
const fs = require('fs');
const items = $input.all().filter((item) => item.json.domain);
const generatedAt = new Date().toISOString();
const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const sevColor = (s) => ({ critical: '#b91c1c', high: '#dc2626', medium: '#d97706', low: '#2563eb', info: '#6b7280' }[s] || '#6b7280');

function loadVulns(item) {
  const s = item.json.scan || {};
  let v = s.vulnerabilities || {};
  const wd = s.workdir || '';
  if ((!v.items || !v.items.length) && wd) {
    const p = `${wd}/vulnerabilities.json`;
    if (fs.existsSync(p)) {
      try { v = JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) {}
    }
  }
  return v;
}

function loadGuard(item) {
  const s = item.json.scan || {};
  if (s.guard) return s.guard;
  const wd = s.workdir || '';
  if (!wd) return null;
  const p = `${wd}/guard_state.json`;
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; }
}

let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Bug Bounty Scan Report</title>
<style>
body{font-family:system-ui,sans-serif;margin:2rem;max-width:1280px}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:14px}
th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top}
th{background:#f3f4f6}
.badge{color:#fff;padding:2px 8px;border-radius:4px;font-size:11px}
.warn{color:#b45309}.muted{color:#6b7280}
.blocked{background:#fef2f2;border:2px solid #dc2626;padding:16px;border-radius:8px;margin:1rem 0}
.blocked h2{color:#b91c1c;margin-top:0}
h2{margin-top:2rem;border-bottom:1px solid #e5e7eb;padding-bottom:6px}
ul.actions{background:#fffbeb;padding:12px 12px 12px 28px;border-radius:8px}
</style></head><body>`;

html += `<h1>Bug Bounty Scan Report</h1><p>Generated: ${esc(generatedAt)}</p>`;
html += `<p class="warn">Automated findings require manual validation for impact and scope.</p>`;

const allVulns = [];
let hostsSummary = [];
let recommended = [];
let anyBlocked = false;
let blockMessages = [];

for (const item of items) {
  const s = item.json.scan || {};
  const v = loadVulns(item);
  const g = loadGuard(item);
  if (s.blocked || g?.blocked) {
    anyBlocked = true;
    blockMessages.push(g?.tester_message || s.tester_message || `Scan stopped for ${item.json.domain}: target may be blocking our IP.`);
    if ((g?.recommendations || []).length) recommended = g.recommendations;
  }
  if ((v.hosts_summary || []).length) hostsSummary = v.hosts_summary;
  if ((v.recommended_actions || []).length && !anyBlocked) recommended = v.recommended_actions;
  for (const f of (v.items || [])) {
    allVulns.push({ ...f, program: item.json.program, apex: item.json.domain });
  }
}

if (anyBlocked) {
  html += '<div class="blocked"><h2>IP / rate limit — scan stopped</h2>';
  html += '<p><strong>The target appears to be blocking or rate-limiting this scanner IP.</strong> All active scan processes were halted to protect your IP and program standing.</p><ul>';
  for (const m of [...new Set(blockMessages)]) html += `<li>${esc(m)}</li>`;
  html += '</ul>';
  if (recommended.length) {
    html += '<h3>What to do next</h3><ul class="actions">';
    for (const a of recommended) html += `<li>${esc(a)}</li>`;
    html += '</ul>';
  }
  html += '</div>';
}

if (hostsSummary.length) {
  html += '<h2>Subdomains scanned</h2><table><tr><th>Host</th><th>Live</th><th>Status</th><th>Title</th><th>Findings</th></tr>';
  for (const h of hostsSummary) {
    html += `<tr>
      <td>${esc(h.host)}</td>
      <td>${h.live ? 'yes' : 'no'}</td>
      <td>${esc(h.status_code ?? '—')}</td>
      <td>${esc(h.title || '')}</td>
      <td>${esc(h.findings_count ?? 0)}</td>
    </tr>`;
  }
  html += '</table>';
}

if (recommended.length && !anyBlocked) {
  html += '<h2>Recommended next steps</h2><ul class="actions">';
  for (const a of recommended) html += `<li>${esc(a)}</li>`;
  html += '</ul>';
}

const byCat = {};
for (const f of allVulns) {
  const c = f.category || f.type || 'other';
  byCat[c] = (byCat[c] || 0) + 1;
}
if (Object.keys(byCat).length) {
  html += '<h2>Findings by category</h2><table><tr><th>Category</th><th>Count</th></tr>';
  for (const [c, n] of Object.entries(byCat).sort((a,b) => b[1]-a[1])) {
    html += `<tr><td>${esc(c)}</td><td>${esc(n)}</td></tr>`;
  }
  html += '</table>';
}

html += '<h2>Detailed findings</h2>';
if (!allVulns.length) {
  html += '<p class="muted">No consolidated findings.</p>';
} else {
  html += '<table><tr><th>Severity</th><th>Host</th><th>Title</th><th>Source</th><th>Recommendation</th></tr>';
  for (const f of allVulns.slice(0, 120)) {
    const sev = (f.severity || 'info').toLowerCase();
    html += `<tr>
      <td><span class="badge" style="background:${sevColor(sev)}">${esc(sev)}</span></td>
      <td>${esc(f.host || f.apex)}</td>
      <td>${esc(f.title)}<br><span class="muted">${esc(f.matched_at || '')}</span></td>
      <td>${esc(f.source)}</td>
      <td>${esc(f.recommendation || '')}</td>
    </tr>`;
  }
  html += '</table>';
}

html += '</body></html>';

const ROOT = '__ROOT__';
const stamp = generatedAt.replace(/[:.]/g, '-');
const reportPath = `${ROOT}/reports/bugbounty-report-${stamp}.html`;
fs.mkdirSync(`${ROOT}/reports`, { recursive: true });
fs.writeFileSync(reportPath, html, 'utf8');

const primaryWorkdir = items[0]?.json?.scan?.workdir || '';
const scanBundle = items.map((item) => ({
  program: item.json.program,
  domain: item.json.domain,
  workdir: item.json.scan?.workdir,
  vulnerabilities: loadVulns(item),
  blocked: !!(item.json.scan?.blocked || loadGuard(item)?.blocked),
}));

return [{
  json: {
    reportPath,
    html,
    summary: scanBundle,
    primary_workdir: primaryWorkdir,
    finding_count: allVulns.length,
    hosts_scanned: hostsSummary.length,
    blocked: anyBlocked,
  },
}];
""".strip().replace("__ROOT__", ROOT))


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    for n in nodes:
        if n["name"] == "Build HTML Report":
            n["parameters"]["jsCode"] = BUILD_REPORT_JS
    conn.execute(
        'UPDATE workflow_entity SET nodes=?, updatedAt=datetime("now"), versionCounter=versionCounter+1 WHERE id=?',
        (json.dumps(nodes), wf_id),
    )
    conn.commit()
    print("Patched Build HTML Report (workdir fallback + IP block banner).")


if __name__ == "__main__":
    main()
