# Cursor Buildathon — Project Submission Document

**Project:** Cyber League  
**Team:** Hackers League  
**Track:** n8n  
**Repository:** https://github.com/Deadsecnote1/cyberleague  
**Demo video:** https://youtu.be/d1xiZMBJ61k  
**Prepared by:** Thanushiyan Kanthasami (Project 1 — Cyber League) · Kiruththiyan Theiventhirarasa (team lead, Project 2 — [Aivura](https://github.com/Kiruthiyan/n8n_aivura))

---

## 01 — Project Overview

### Project name & one-line pitch

**Cyber League** — A local command center that triggers an **n8n-orchestrated** web pentest pipeline with configurable scope, SQL injection checks, rate-limit protection, and optional OpenAI hunt advisor — for **authorized** bug bounty and lab testing.

### Summary

Security testers often run subdomain enumeration, HTTP probing, template scanners, and manual SQLi checks in disconnected tools. Cyber League unifies these steps behind a single **n8n workflow**: the FastAPI portal collects target URL, scan preset, and pentest scope, then triggers n8n via webhook. n8n executes `bugbounty-scan.sh`, which runs industry tools (subfinder, httpx, ffuf, nuclei, nmap, nikto) plus a dedicated SQLi phase. Results are aggregated into `vulnerabilities.json` and HTML reports; optional AI summarizes priorities before and after the scan. The system is designed for Parrot/Kali-style Linux workstations and refuses to scan targets outside user-defined scope.

### Submission details

| Field | Value |
|-------|--------|
| Track | **n8n** — workflow is the sole scan engine; portal does not run tools directly |
| Track integration | Webhooks, form triggers, Code nodes, Execute Command, AI nodes, workflow patch tooling |
| Team | Hackers League |
| Demo | https://youtu.be/d1xiZMBJ61k |
| Repository | https://github.com/Deadsecnote1/cyberleague |

---

## 02 — Problem Statement

### The problem

Bug bounty and web pentest recon involves many repetitive steps: discover subdomains, identify live hosts, check security headers, run template scanners, test for SQL injection, and document findings. Testers switch between terminals, scripts, and notes. Without scope discipline, automated subdomain enumeration can probe **out-of-scope** hosts. Without rate awareness, scanners trigger WAF blocks and waste program time.

### Why it matters

- Occurs on **every** web engagement (daily for bounty hunters, weekly for consultancies).
- Consequence: missed coverage, false positives, program violations, and IP blocks that halt testing.
- Current workaround: manual shell scripts + Burp + scattered notes — no single orchestrated view, no guardrails.

### Root cause

Tooling is powerful but **not orchestrated** with program rules, guardrails, and a single audit trail. Orchestration platforms (n8n) are rarely wired to real pentest CLIs with scope and safety defaults.

---

## 03 — Proposed Solution

### What the product does

**Cyber League** provides a browser UI to configure and launch scans. Configuration includes target URL, scan intensity preset, pentest scope (in/out lists), and toggles for SQLi and AI. On submit, the portal validates scope and POSTs to n8n. n8n runs a published workflow that executes the worker script, generates reports, and optionally calls OpenAI. The dashboard lists past runs with severity counts and links to HTML reports.

### Key features (built & demonstrable)

| Feature | User need addressed |
|---------|---------------------|
| n8n webhook + form triggers | Reliable engine integration for the n8n track |
| Quick / Standard / Deep presets | Time-boxed scans vs deep assessment |
| Pentest scope (3 modes + templates) | Stay within program boundaries |
| SQL injection phase | Dedicated sqli templates + safe probes |
| Rate-limit / IP-block guard | Stop when target blocks scanner |
| Unified `vulnerabilities.json` + HTML report | Single view of findings |
| AI pre/post-scan advisor | Prioritization and narrative summary |
| Delete scan run | GDPR / lab cleanup from UI |
| `cyberleague.sh` / `shutdown.sh` | One-command ops |

### Scope

**In scope (this build):** Single-target web recon on Linux; n8n-orchestrated pipeline; local portal; file-based artifacts; authorized/lab targets.

**Out of scope (deliberate):** Cloud SaaS hosting; multi-tenant auth; authenticated crawling; full sqlmap exploitation; Windows-native install; CI/CD deployment.

---

## 04 — Functional Requirements

### Must have (all demonstrable)

| ID | Requirement |
|----|-------------|
| M1 | User submits target URL and preset from portal; scan starts via n8n |
| M2 | n8n workflow executes `bugbounty-scan.sh` with profile env vars |
| M3 | Light scan produces subdomain list, live hosts, header/TLS notes |
| M4 | Findings aggregated to `vulnerabilities.json` and HTML report |
| M5 | Portal dashboard lists runs with severity breakdown |
| M6 | Pentest scope validated before scan; hosts filtered during scan |
| M7 | Rate-limit guard can halt scan and record blocked state |

### Should have

| ID | Requirement |
|----|-------------|
| S1 | SQL injection checks (nuclei sqli + probes) |
| S2 | OpenAI pre/post-scan advisor (graceful without API key) |
| S3 | Deep profile (nmap, nuclei, nikto) |
| S4 | Delete run removes `scans/` workdir and related reports |
| S5 | n8n Executions visible for audit |

### Could have / Won't have (this build)

| Item | Decision |
|------|----------|
| Docker Compose | Won't — GitHub-only delivery for buildathon |
| Public cloud demo URL | Won't — local 127.0.0.1 only |
| Burp export | Could — future |
| Multi-target CSV from portal | Partial — n8n CSV path exists; portal focuses single URL |

---

## 05 — Non-Functional Requirements

### Performance

- Quick preset: ~5–15 minutes on lab targets (5 hosts, no per-host FFUF/Nuclei).
- Portal UI responses &lt; 2s for dashboard (local filesystem).
- n8n webhook returns immediately (`onReceived`); long work runs in execution.

### Reliability & error handling

- Missing CLI tools logged in `tools_missing`; scan continues.
- OpenAI failures skip AI nodes without failing workflow.
- Webhook 404 → portal falls back to n8n form trigger.
- Invalid scope → portal error, no scan started.
- `.scan_stop` + `emit_final_json` on guard trip or runtime cap.

### Usability

- Dark-themed portal; presets with ETA hints; scope section with templates.
- Local-only binding (`127.0.0.1`) reduces accidental exposure.

### Scalability

- Filesystem storage suits single analyst. For team scale: object storage for `scans/`, queue-backed workers, horizontal n8n workers. Current design intentionally simple for hackathon demo.

---

## 06 — Technical Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for diagram and stack table.

### System overview

Portal (FastAPI) → n8n webhook → Parse → AI (optional) → Execute Command → `bugbounty-scan.sh` → aggregate → HTML report → AI post (optional).

### Technology stack

n8n, FastAPI, uvicorn, Bash, Python 3, subfinder/httpx/ffuf/nuclei/nmap/nikto/curl, OpenAI API, SQLite (n8n internal DB).

### Data flow (core action)

1. POST `/scan` with `target_url`, `scan_config`, `scope`.
2. Sidecar files: `.current_scan_domain`, `.current_scan_env`, `.current_scan_scope.json`.
3. n8n runs worker; writes `scans/<domain>_<UTC>/`.
4. `aggregate_vulnerabilities.py` → `vulnerabilities.json`.
5. Report node writes `reports/bugbounty-report-*.html`.

### AI integration

- **Provider:** OpenAI (`gpt-4o-mini` default).
- **Role:** Pre-scan prioritization notes; post-scan executive summary merged into report.
- **Prompting:** Via `scripts/ai_pentest_advisor.py` with target + findings bundle.
- **Failure:** Workflow continues if key missing or API errors.

### Known technical limitations

- Linux-only workers; hardcoded paths in some n8n patches (configurable via `ROOT`).
- n8n workflow must be Active after DB patches.
- SQLi detection ≠ confirmed exploitation.
- Single-machine filesystem storage.

---

## 07 — Security

### Authentication & authorisation

- Portal binds to **127.0.0.1** only — no remote access by default.
- No login (single-operator local tool). n8n admin access assumed trusted.

### Data handling

- Scan artifacts stored locally under `scans/` and `reports/`.
- No PII collection by application; user-supplied targets only.
- Delete run removes workdir and stamp-matched reports.

### API & secret management

- `OPENAI_API_KEY` in `config/openai.env` (gitignored pattern; example file has placeholder only).
- Keys not sent to browser; AI runs server-side in n8n/worker context.
- Portal does not embed secrets in frontend.

### Input validation

- Path traversal blocked on `run_id` and report filenames.
- Scope validation on target URL and host lists.
- n8n Code nodes validate required `target_url`.

### Known gaps

- No TLS on local HTTP (localhost only).
- n8n default auth if exposed to network — operator must firewall.
- Automated scanning can be destructive on misconfigured targets — user responsibility.

---

## 08 — User Stories & Use Cases

### Core user stories

1. As a **tester**, I want to start a quick recon scan from a browser, so that I get subdomains and headers in one step.
2. As a **tester**, I want n8n to orchestrate tools, so that I can audit and extend the pipeline visually.
3. As a **tester**, I want to define in-scope hosts, so that I do not scan out-of-scope subdomains.
4. As a **tester**, I want SQLi checks included, so that obvious injection issues surface early.
5. As a **tester**, I want the scan to stop if the target rate-limits me, so that I do not burn the program IP.
6. As a **tester**, I want an HTML report, so that I can share results with my team.
7. As a **tester**, I want AI to summarize findings, so that I know what to validate first.
8. As a **tester**, I want to delete old lab runs, so that my disk stays clean.

### Primary use case walkthrough

1. User opens Cyber League → **New scan**.
2. Enters `http://testphp.vulnweb.com`, loads vulnweb scope template, selects **Quick**, enables SQLi + AI.
3. Portal validates scope → POST webhook → n8n execution starts.
4. Worker creates `scans/testphp.vulnweb.com_<timestamp>/`, runs light + SQLi, writes `vulnerabilities.json`.
5. n8n builds HTML report; AI writes post-scan markdown.
6. User opens **Dashboard** → **View** run → reads findings and downloads report.

### Edge cases

- Target outside scope → portal error, no execution.
- n8n down → portal shows engine offline.
- Tool missing → recorded in scan JSON, scan continues.
- Block detected → `.scan_stop`, partial results retained.

---

## 09 — Target Users & Market

### Primary user

Junior-to-mid **bug bounty hunters** and **pentest lab students** on Linux (Parrot/Kali) who want orchestrated recon without building custom scripts.

### Market opportunity

Bug bounty platforms continue to grow; automation with guardrails is underserved for solo hunters. Initial segment: thousands of active researchers using Linux toolchains.

### Competitive landscape

| Alternative | Weakness |
|-------------|----------|
| Manual script collections | No visual orchestration, weak scope model |
| Commercial ASM platforms | Costly, not local-first, overkill for labs |
| Raw n8n without pentest pack | No scope/SQLi/guard integration out of the box |

---

## 10 — Business Model

### Revenue model

**Freemium SaaS** (future): free local runner; paid cloud for team dashboards, report branding, and compliance exports.

### Pricing hypothesis

$19–49/month per researcher for cloud sync and team features; local runner remains free/open core.

### Go-to-market

- Publish workflow template on n8n community
- YouTube/Twitch lab demos on vulnweb targets
- University cybersecurity clubs

### Roadmap

| Horizon | Deliverable |
|---------|-------------|
| Now | Cyber League + n8n workflow + docs (buildathon) |
| 0–3 months | Docker Compose, path-agnostic config, Burp export |
| 12 months | Team cloud, program CSV import, authenticated scans |

---

## 11 — Why This Project Leads the Track

### Technical edge (n8n)

- **Deep n8n usage:** webhook ingress, Code parsing, Execute Command worker, AI nodes, form fallback — not a superficial integration.
- Workflow patch suite (`patch_*.py`) shows repeatable deploy story.
- Portal ↔ n8n contract via JSON payload + sidecar files solves real v2 pain points (`fs`, Execute Command disabled by default).

### Problem–solution fit

Directly addresses fragmented recon + scope violations with one visual pipeline testers can extend without recompiling the portal.

### Execution quality

- End-to-end demo: portal → n8n → artifacts → report → AI.
- Presets match real time budgets; scope + SQLi + guard are differentiators for a 24h-style build.
- Polished local UI; operator scripts `cyberleague.sh` / `shutdown.sh`.

### Real-world potential

Extends beyond hackathon: hunters can fork workflow, add nuclei templates, plug Jira export. n8n marketplace distribution fits track sponsor goals.

---

## 12 — Team & Roles

**Hackers League** submitted two n8n-track projects for Cursor Buildathon:

| | Project 1 | Project 2 |
|---|-----------|-----------|
| **Name** | **Cyber League** | **Aivura** |
| **Pitch** | Local command center for an n8n-orchestrated bug-bounty / web pentest pipeline | AI academic co-pilot on Telegram — lecture PDFs, deadlines, and study questions via orchestrated n8n workflows |
| **Builder / lead** | Thanushiyan Kanthasami | Kiruththiyan Theiventhirarasa (team lead) |
| **Repository** | https://github.com/Deadsecnote1/cyberleague | https://github.com/Kiruthiyan/n8n_aivura |
| **Demo** | https://youtu.be/d1xiZMBJ61k | https://t.me/Aivura_bot (`@Aivura_bot`) |
| **This document** | Sections 01–11 below | Summary from Kiruththiyan’s submission PDF |

### Team members

| Name | Role | Contribution |
|------|------|--------------|
| **Thanushiyan Kanthasami** | Builder — Project 1 (Cyber League) | Portal (FastAPI), n8n webhook integration, `bugbounty-scan.sh`, scope + SQLi modules, rate-limit guard, AI advisor scripts, workflow patches, ops scripts, documentation |
| **Kiruththiyan Theiventhirarasa** | Team lead — Project 2 (Aivura) | Router + 11 feature n8n sub-workflows, Telegram bot, Gemini 2.0 Flash (intent + vision), Notion user registry, Gmail/Notion context, workflow JSON generator, React admin portal (Cursor/Vite), security patterns, submission doc |

### Project 2 — Aivura (summary)

University students juggle assignments, email, Drive, and study tools across disconnected apps. **Aivura** gives one Telegram interface: students message `@Aivura_bot`, upload PDFs, or use slash commands; n8n verifies Chat ID (Notion or demo allowlist), classifies intent, routes to one of 11 feature sub-workflows, and returns structured four-section Markdown replies (Summary, Findings, Actions, Draft/Plan).

**Highlights:** 12 n8n workflows (1 router + 11 features — PDF summary, MCQ, study plan, deadlines, viva prep, flashcards, etc.); admin portal for cohort access; demo mode for hackathon testing; secrets via n8n environment variables only.

### Why this team

Thanushiyan connects n8n to real pentest CLIs and local scope controls for **authorized** security testing. Kiruththiyan delivers production-style n8n routing (Switch + Execute Workflow), multi-API orchestration, and a student-facing channel students already use. Together, Hackers League shows two strong **Best Use of n8n** patterns: security pipeline automation and academic workflow automation.

---

*Cyber League · Hackers League · Cursor Buildathon · n8n track*
