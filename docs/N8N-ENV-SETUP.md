# n8n environment variables

Set these in **n8n → Settings → Variables** (or instance `.env`):

| Variable | Required | Notes |
|----------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Yes | From `@BotFather` — same as root `.env` |
| `GEMINI_API_KEY` | Yes | Google Gemini — intent + replies |
| `NOTION_API_KEY` | Yes | Integration token |
| `NOTION_USERS_DATABASE_ID` | Yes | Student registry |
| `NOTION_STUDENT_DATABASE_ID` | For study/deadlines | Tasks DB |
| `GMAIL_ACCESS_TOKEN` | Optional | Study plan / deadlines |
| `AIVURA_DEMO_MODE` | Optional | `true` = skip Notion, use allowlist |
| `DEMO_ALLOWED_CHAT_IDS` | Optional | Comma Chat IDs; empty = allow all in demo |
| `GOOGLE_ACCESS_TOKEN` | Optional | Alias for Gmail |

Local copy: project root `.env` (gitignored).

After import, on **01 – Telegram Trigger** add Telegram credential OR rely on `$env.TELEGRAM_BOT_TOKEN` in HTTP nodes.

Bot: [@Aivura_bot](https://t.me/Aivura_bot)
