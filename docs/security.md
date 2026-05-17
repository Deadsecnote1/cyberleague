# Security – Aivura

## Secrets management
- **Never** commit `.env`, tokens, or credential exports
- Use `.env.example` with empty placeholders only
- Workflow JSON uses `$env.VARIABLE_NAME` expressions only
- Rotate all keys after public demos or screen recordings

## Principle of least privilege

| Service | Recommended scope |
|---------|-------------------|
| OpenAI | Project key with usage limits |
| Telegram | Single bot per environment |
| Notion | Integration limited to required databases |
| Gmail | Read-only |
| Google Drive | Folder-scoped access |

## Data handling
- User messages pass through n8n execution logs—secure your n8n instance
- Notion logs may store message metadata—define retention policy
- Do not log full email bodies in production without consent

## Telegram
- Validate `chat_id` is from expected users for private deployments
- For public bots, avoid returning internal errors verbatim to users

## n8n hardening
- Enable authentication on self-hosted n8n
- Restrict who can edit workflows
- Use separate env for staging vs production

## Compliance checklist (hackathon → production)
- [ ] Privacy policy for stored messages
- [ ] User opt-in for Gmail/Drive access
- [ ] Data deletion process
- [ ] Rate limiting on OpenAI calls
- [ ] Audit log access controls

## Incident response
1. Revoke compromised token at provider
2. Rotate env vars in n8n
3. Review execution logs for abuse
4. Re-import workflows if JSON was tampered
