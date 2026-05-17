# Setup – Aivura (Students Only)

## 1. Prerequisites
- n8n (Cloud or self-hosted)
- OpenAI API key
- Telegram bot ([@BotFather](https://t.me/BotFather))
- Notion integration
- Optional: Google Gmail + Drive tokens

## 2. Environment

Copy `.env.example` → `.env` and fill:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | AI responses |
| `TELEGRAM_BOT_TOKEN` | Bot |
| `NOTION_API_KEY` | Databases |
| `NOTION_USERS_DATABASE_ID` | Registered students |
| `NOTION_STUDENT_DATABASE_ID` | Student tasks |
| `GOOGLE_ACCESS_TOKEN` / `GMAIL_ACCESS_TOKEN` | Email |
| `GOOGLE_DRIVE_FOLDER_ID` | Study files |

Portal: `portal/.env` → `VITE_ADMIN_PASSWORD`

## 3. Notion Users DB

Properties:
- **Name** (title)
- **Telegram Chat ID** (rich text)
- **Role** (rich text) → `student`
- **Active** (checkbox)

## 4. Import n8n (9 workflows)

1. Import all JSON files from `workflows/student/` (8 feature workflows)
2. Import `workflows/00-main-router-workflow.json`
3. Link each **RUN – …** node in the router to the matching student workflow
4. Add Telegram credential on trigger node
5. Activate router

## 5. Admin Portal

```bash
cd portal && npm install && npm run dev
```

Add each student with Telegram Chat ID → export JSON → sync to Notion.

## 6. Test

See `workflows/student/TELEGRAM-TESTS.md`
