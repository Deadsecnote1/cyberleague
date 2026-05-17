# Demo Script (2 min) — Aivura · n8n Track

**Goal:** Prove orchestration depth, not just “ChatGPT in Telegram.”

## 0:00–0:10 — n8n Router (judge hook)
- Open `Aivura – Telegram Bot Router` in n8n
- Point to: Telegram Trigger → Notion auth → Switch → **8 Execute Workflow** nodes

## 0:10–0:25 — Admin Portal
- Add student: Name + **Telegram Chat ID** + Active
- Mention: export → Notion Users DB (or pre-seeded for live demo)

## 0:25–0:35 — Access control
- Telegram from **unregistered** number → “Not registered” deny message

## 0:35–0:45 — Commands
- Registered student: `/help` → command list

## 0:45–1:15 — PDF pipeline (hero moment)
- Upload PDF + caption: “Summarize chapter 2 for exam”
- Show n8n execution: sub-workflow `01-pdf-summary` ran
- Show 4-section Markdown reply on phone

## 1:15–1:35 — Second workflow
- `/mcq binary search trees` → `02-generate-mcq` execution

## 1:35–2:00 — Optional power move
- `/studyplan finals in 5 days` → Gmail + Notion nodes in `04-study-plan`
- Or show execution log with `api_errors` empty vs. graceful fallback

## Backup if live API fails
- Pre-record 30s screen capture of successful execution
- Show imported workflow JSON count: **9 files** in repo
