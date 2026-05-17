# Aivura — 15-minute setup

## Checklist

- [ ] Telegram bot: [@Aivura_bot](https://t.me/Aivura_bot) token in n8n `TELEGRAM_BOT_TOKEN`
- [ ] Gemini key in n8n `GEMINI_API_KEY`
- [ ] Notion integration + Users DB with properties (Name, Telegram Chat ID, Role, Active)
- [ ] `NOTION_USERS_DATABASE_ID` in n8n
- [ ] Import 8 × `workflows/student/*.json`
- [ ] Import `workflows/00-main-router-workflow.json` + link RUN nodes
- [ ] Activate router
- [ ] Portal: add student Chat ID → export → Notion rows
- [ ] Test `/help` from registered Chat ID

## Verify locally

```bash
node scripts/verify-setup.mjs
```

## Demo order (judges)

1. n8n router canvas (8 Execute Workflow branches)
2. Portal → add user
3. Telegram deny (unregistered)
4. Telegram `/help` + PDF summary
5. n8n execution log
