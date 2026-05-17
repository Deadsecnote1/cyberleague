# Cyber League

**Hackers League** · Cursor Buildathon · **n8n track** · branch **`cyber-league`**

> **Team repo:** [Deadsecnote1/cyberleague](https://github.com/Deadsecnote1/cyberleague) — see [`BRANCHES.md`](BRANCHES.md) for **Project 2 (Aivura)** on branch `aivura`.

Local command center for an **n8n-orchestrated** bug-bounty / web pentest pipeline. The portal triggers scans; **n8n** runs the workflow; **bash/Python workers** execute tools. Findings land in `scans/` and HTML reports in `reports/`.

> **Authorized testing only.** Use deliberately vulnerable labs or targets you own / are in scope for. The pipeline includes rate-limit guards and configurable **pentest scope** to reduce out-of-scope probing.

## Demo & submission

| Item | Link |
|------|------|
| **Project 1 — Cyber League** (this repo) | https://github.com/Deadsecnote1/cyberleague |
| Project 1 demo video | https://youtu.be/d1xiZMBJ61k |
| **Project 2 — Aivura** (Kiruththiyan) | https://github.com/Kiruthiyan/n8n_aivura |
| Project 2 demo (Telegram) | https://t.me/Aivura_bot |
| Submission write-up | [docs/CURSOR_BUILDATHON_SUBMISSION.md](docs/CURSOR_BUILDATHON_SUBMISSION.md) |
| Submission PDF | [docs/submissions/Cyber_League_Cursor_Buildathon_Submission.pdf](docs/submissions/Cyber_League_Cursor_Buildathon_Submission.pdf) |
| Video script | [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md) |

## Architecture (short)

```
Cyber League Portal (FastAPI, :8765)
        │  webhook / form
        ▼
n8n — Bug Bounty Pentest Pipeline
        │  Execute Command + Code nodes
        ▼
scripts/bugbounty-scan.sh  →  subfinder, httpx, ffuf, nuclei, nmap, nikto, SQLi
        │
        ▼
scans/<domain>_<timestamp>/  +  reports/*.html
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data flow.

## Requirements

- **Linux** (tested on Parrot OS / Debian-based). Bash, Python 3.10+.
- **n8n** v2 with Execute Command nodes enabled (see [docs/N8N_SETUP.md](docs/N8N_SETUP.md)).
- Optional CLI tools (pipeline degrades gracefully if missing): `subfinder`, `httpx`, `ffuf`, `nmap`, `nuclei`, `nikto`, `curl`.
- Optional **OpenAI** key for AI pre/post-scan advisor.

Not supported: native Windows/macOS installs (WSL may work with manual tool setup; not validated).

## Quick start

```bash
git clone https://github.com/Deadsecnote1/cyberleague.git
cd cyberleague

# Optional: AI advisor
cp config/openai.env.example config/openai.env
# edit config/openai.env — add OPENAI_API_KEY

# Import & activate n8n workflow (once) — see docs/N8N_SETUP.md
# python3 scripts/patch_all_workflow.py  # if using local n8n DB

# Start stack (n8n + portal)
chmod +x cyberleague.sh shutdown.sh
./cyberleague.sh
```

Open **http://127.0.0.1:8765** → **New scan** → pick **Quick** preset → use an **authorized** target (e.g. `http://testphp.vulnweb.com`).

Stop everything:

```bash
./shutdown.sh
```

## Project layout

```
cyberleague/
├── cyberleague.sh          # Start n8n + portal
├── shutdown.sh             # Stop services & scan workers
├── portal/                 # Cyber League UI (FastAPI)
├── scripts/                # Scan workers, patches, scope, SQLi
├── n8n/                    # Exported workflow JSON
├── config/
│   ├── openai.env.example
│   └── scopes/             # Scope templates for portal
├── scans/                  # Per-run artifacts (gitignored recommended)
├── reports/                # HTML + AI markdown reports
└── docs/                   # Buildathon & operator docs
```

## Scan profiles (portal presets)

| Preset | Profile | Typical time | Notes |
|--------|---------|--------------|--------|
| **Quick** | light | ~5–15 min | 5 hosts, no per-host FFUF/Nuclei |
| **Standard** | light | ~15–30 min | FFUF on up to 10 hosts |
| **Deep** | both | ~45–90+ min | Light + deep (nmap, nuclei, nikto) |

Features: **pentest scope**, **SQL injection checks** (nuclei + safe probes), **rate-limit / IP-block guard**, **delete run** from dashboard.

## Environment (n8n / workers)

Critical for n8n v2:

```bash
export NODES_EXCLUDE='[]'
export NODE_FUNCTION_ALLOW_BUILTIN='fs,path,os,crypto,util'
```

`cyberleague.sh` sets these automatically.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/CURSOR_BUILDATHON_SUBMISSION.md](docs/CURSOR_BUILDATHON_SUBMISSION.md) | Full buildathon submission (12 sections) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, AI integration |
| [docs/N8N_SETUP.md](docs/N8N_SETUP.md) | Workflow import, activate, troubleshoot |
| [docs/SCOPE.md](docs/SCOPE.md) | Pentest scope configuration |
| [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md) | ~3 min recording script |

## Team

**Hackers League**

- **Thanushiyan Kanthasami** — **Project 1: Cyber League** (this repo): portal, n8n integration, scan workers, scope, SQLi, AI advisor, ops scripts.
- **Kiruththiyan Theiventhirarasa** (team lead) — **Project 2: [Aivura](https://github.com/Kiruthiyan/n8n_aivura)** — AI academic co-pilot on Telegram (`@Aivura_bot`); 12 n8n workflows (router + 11 feature flows), Gemini, Notion/Gmail, React admin portal. Demo: https://t.me/Aivura_bot

## License & ethics

For education and authorized security testing only. You are responsible for complying with program rules and local law.
