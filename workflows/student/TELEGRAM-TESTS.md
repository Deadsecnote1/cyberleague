# Telegram Tests

| Command | Workflow file |
|---------|---------------|
| /summary | student/01-pdf-summary.json |
| /mcq | student/02-generate-mcq.json |
| /submit | student/03-submission-answer.json |
| /studyplan | student/04-study-plan.json |
| /deadlines | student/05-deadlines.json |
| /viva | student/06-viva-prep.json |
| /lecture | student/07-lecture-summary.json |
| /flashcards | student/09-flashcards.json |
| /today | student/10-today.json |
| /simple | student/11-simple.json |
| /ask | student/08-general-ask.json |

## PDF
Send PDF with caption: Summarize chapter 2

## Demo (no Notion)
n8n: `AIVURA_DEMO_MODE=true` + optional `DEMO_ALLOWED_CHAT_IDS=your_id`

## Broadcast (admin)
Portal → Broadcast, or `node scripts/broadcast.mjs --message "Hi" --ids YOUR_ID`

## Natural
"Create 10 MCQs on binary search"
