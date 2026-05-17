# Aivura

**AI academic co-pilot for university students on Telegram** — orchestrated with **n8n**, built with **Cursor**.

Students get structured study help (summaries, MCQs, viva prep, deadlines) in one chat. Admins control access by Telegram Chat ID. No student signup, no separate app.

| | |
|---|---|
| **Telegram bot** | [@Aivura_bot](https://t.me/Aivura_bot) |
| **Repository** | [github.com/Deadsecnote1/cyberleague](https://github.com/Deadsecnote1/cyberleague) (branch: `aivura`) |
| **Track** | Cursor Buildathon · Best use of n8n |
| **Students** | Telegram only |
| **Admins** | React portal → Notion user registry |

---

## Why Aivura

| Generic ChatGPT / Gemini | Aivura |
|--------------------------|--------|
| General chat in browser | **Telegram** — already on every phone |
| No cohort access control | **Admin-managed** Chat ID allowlist |
| One long reply | **Fixed 4-section** format (mobile-friendly) |
| Manual prompts | **Slash commands** — one job per workflow |
| No deadline context | Optional **Gmail + Notion** for plans/deadlines |

Aivura is not a replacement for the model — it is **gated, routed academic automation** on top of Gemini.

---

## Features

- **11 dedicated n8n workflows** — one feature each (no monolithic bot logic)
- **Router workflow** — auth → intent → Switch → Execute Workflow → reply
- **Gemini 2.0 Flash** — intent classification + all student responses
- **Gemini Vision** — PDF and image text extraction for summaries
- **Demo mode** — run without Notion (`AIVURA_DEMO_MODE`)
- **Admin portal** — add students, export to Notion, broadcast messages
- **Workflow generator** — regenerate all JSON from a single script

---

## Student commands

| Command | Description |
|---------|-------------|
| Send **PDF** (+ caption) | Document summary (auto-routes to summary) |
| `/summary` | Summarize PDF or notes |
| `/mcq` | Generate multiple-choice questions |
| `/submit` | Assignment answer structure (study aid) |
| `/studyplan` | Multi-day study schedule |
| `/deadlines` | Urgent due dates and tasks |
| `/viva` | Viva questions + model answers |
| `/lecture` | Lecture notes summary |
| `/flashcards` | Revision flashcards |
| `/today` | Plan for the next few hours |
| `/simple` | Explain a topic in simple language |
| `/ask` | General study question |
| `/help` | List all commands |

Every AI reply uses four Markdown sections: **Quick Summary · Important Findings · Suggested Next Actions · Draft / Plan / Checklist**.

---

## Architecture

```
┌──────────────┐     webhook      ┌─────────────────────────────────┐
│   Student    │ ───────────────► │  n8n: Main Router Workflow      │
│   Telegram   │                  │  Extract → Auth → Intent → Switch│
└──────────────┘                  └───────────────┬─────────────────┘
        ▲                                         │
        │              ┌──────────────────────────┼──────────────────────────┐
        │              ▼                          ▼                          ▼
        │     ┌────────────────┐        ┌────────────────┐       ┌────────────────┐
        │     │ PDF / Lecture  │  …     │ Study / Today  │       │ MCQ / Viva / … │
        │     │ Gemini Vision  │        │ Gmail + Notion │       │ Gemini only    │
        │     └────────┬───────┘        └────────┬───────┘       └────────┬───────┘
        │              └──────────────────────────┴──────────────────────────┘
        └──────────────────────────── Markdown reply ────────────────────────────┘

┌─────────────────┐   export / sync   ┌─────────────────┐
│  Admin Portal   │ ────────────────► │  Notion Users   │
│  (React/Vite)   │                   │  Database       │
└─────────────────┘                   └─────────────────┘
```

**12 n8n workflow files:** `00-main-router-workflow.json` + 11 files under `workflows/student/`.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Orchestration | **n8n** (Telegram Trigger, HTTP, Code, Switch, Execute Workflow) |
| AI | **Google Gemini 2.0 Flash** (chat + vision) |
| Messaging | **Telegram Bot API** |
| User registry | **Notion API** |
| Optional context | Gmail API, Notion Student DB |
| Admin UI | React 19, Vite, TypeScript, Tailwind CSS |
| Development | **Cursor** |
| Codegen | `scripts/build-aivura-student-bot.mjs` |

---

## Quick start

### Prerequisites

- [n8n](https://n8n.io) (Cloud or self-hosted)
- [Google AI Studio](https://aistudio.google.com/apikey) API key (Gemini)
- Telegram bot token ([@BotFather](https://t.me/BotFather))
- Notion integration (optional; use demo mode without it)

### 1. Clone and configure

```bash
git clone -b aivura https://github.com/Deadsecnote1/cyberleague.git
cd cyberleague
cp .env.example .env
```

Fill in `.env` (see [Environment variables](#environment-variables)). Mirror the same values in **n8n → Settings → Variables**.

### 2. Admin portal

```bash
cd portal
npm install
cp .env.example .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Default password: set `VITE_ADMIN_PASSWORD` in `portal/.env` (e.g. `aivura2026`).

- Add students with **Telegram Chat ID** ([@userinfobot](https://t.me/userinfobot))
- **Export** JSON → import into Notion Users database
- **Broadcast** — optional; see [Admin broadcast](#admin-broadcast)

### 3. Notion Users database

| Property | Type | Value |
|----------|------|--------|
| Name | Title | Student name |
| Telegram Chat ID | Rich text | Numeric Chat ID |
| Role | Rich text | `student` |
| Active | Checkbox | `true` to allow access |

Share the database with your Notion integration. Set `NOTION_USERS_DATABASE_ID` in n8n.

### 4. Import n8n workflows

1. Import all JSON files from `workflows/student/` (11 workflows)
2. Import `workflows/00-main-router-workflow.json`
3. Open the router → link each **RUN – …** node to the matching student workflow
4. **Activate** the router workflow (registers Telegram webhook)

Detailed steps: [docs/N8N-ENV-SETUP.md](docs/N8N-ENV-SETUP.md) · [docs/QUICK-START.md](docs/QUICK-START.md)

### 5. Verify and test

```bash
node scripts/verify-setup.mjs
```

Message [@Aivura_bot](https://t.me/Aivura_bot) with `/help` from a registered Chat ID.

Test matrix: [workflows/student/TELEGRAM-TESTS.md](workflows/student/TELEGRAM-TESTS.md)

---

## Demo mode (no Notion)

For hackathons or local demos without Notion:

| n8n variable | Value |
|--------------|--------|
| `AIVURA_DEMO_MODE` | `true` |
| `DEMO_ALLOWED_CHAT_IDS` | `123456789` (comma-separated; leave empty to allow any ID) |

Re-import or update the router after changing env vars.

---

## Admin broadcast

Send a message to all active students:

**Portal:** Sidebar → **Broadcast** (optional `VITE_TELEGRAM_BOT_TOKEN` in `portal/.env`)

**CLI:**

```bash
node scripts/broadcast.mjs --message "Exams start Monday 9am" --ids CHAT_ID_1,CHAT_ID_2
# or
node scripts/broadcast.mjs --file aivura-students-notion.json --message "Hello cohort"
```

---

## Environment variables

| Variable | Required | Where |
|----------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Yes | n8n, `.env` |
| `GEMINI_API_KEY` | Yes | n8n, `.env` |
| `NOTION_API_KEY` | Yes* | n8n |
| `NOTION_USERS_DATABASE_ID` | Yes* | n8n |
| `NOTION_STUDENT_DATABASE_ID` | No | Study plan / deadlines / today |
| `GMAIL_ACCESS_TOKEN` | No | Email context |
| `AIVURA_DEMO_MODE` | No | Skip Notion auth |
| `DEMO_ALLOWED_CHAT_IDS` | No | Demo allowlist |
| `VITE_ADMIN_PASSWORD` | Portal | `portal/.env` |

\*Not required when demo mode is enabled.

---

## Regenerate workflows

After editing `scripts/build-aivura-student-bot.mjs`:

```bash
node scripts/build-aivura-student-bot.mjs
```

Re-import changed JSON files into n8n and re-link Execute Workflow nodes if names changed.

---

## Project structure

```
lifepilot-ai/
├── portal/                 # Admin portal (React + Vite)
│   └── src/pages/          # Dashboard, Users, Broadcast, Workflows, …
├── workflows/
│   ├── 00-main-router-workflow.json
│   └── student/            # 11 feature workflows + TELEGRAM-TESTS.md
├── scripts/
│   ├── build-aivura-student-bot.mjs
│   ├── verify-setup.mjs
│   └── broadcast.mjs
├── docs/                   # Setup, security, Buildathon submission
├── .env.example
└── README.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/QUICK-START.md](docs/QUICK-START.md) | 15-minute setup checklist |
| [docs/N8N-ENV-SETUP.md](docs/N8N-ENV-SETUP.md) | n8n variables and import order |
| [docs/demo-script.md](docs/demo-script.md) | 2-minute live demo script |
| [docs/CURSOR-BUILDATHON-SUBMISSION.md](docs/CURSOR-BUILDATHON-SUBMISSION.md) | Full competition submission (source) |
| [docs/CURSOR-BUILDATHON-SUBMISSION.pdf](docs/CURSOR-BUILDATHON-SUBMISSION.pdf) | **Submission PDF** (print/submit) |
| [docs/architecture.md](docs/architecture.md) | System design overview |
| [docs/security.md](docs/security.md) | Secrets and hardening |

---

## Important notes

1. **One engine per bot token** — Run either n8n (webhook) or the legacy Python [`aivura-agent`](https://github.com/Kiruthiyan/aivura-agent) (polling), not both on the same token.
2. **Secrets** — Never commit `.env`. Use `$env.*` in workflow JSON only.
3. **Bot not replying?** — Router must be **active** in n8n; webhook must be set. Run `node scripts/verify-setup.mjs`.
4. **Rotate keys** if tokens were shared in chat or recordings.

---

## License

MIT — see repository for details. Built for educational and hackathon use; verify AI outputs before academic submission.

---

**Aivura** · Cursor × n8n · [@Aivura_bot](https://t.me/Aivura_bot)
