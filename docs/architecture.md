# Aivura Architecture (Student Only)

## Users
- **Students** → Telegram bot only
- **Admin** → Portal only (add students, export to Notion)

## Router
1. Telegram message (+ optional PDF document)
2. Query `NOTION_USERS_DATABASE` by `Telegram Chat ID`
3. Deny if not found / inactive
4. OpenAI intent classification
5. Switch → run **one** student workflow (8 separate n8n workflows)
6. Send Markdown reply

## Student workflows (8 files, one feature each)
| Intent | Trigger |
|--------|---------|
| DOCUMENT_SUMMARY | PDF upload or `/summary` |
| GENERATE_MCQ | `/mcq` or "create quiz" |
| SUBMISSION_ANSWER | `/submit` |
| STUDY_PLAN | `/studyplan` |
| ASSIGNMENT_DEADLINES | `/deadlines` |
| VIVA_PREP | `/viva` |
| LECTURE_SUMMARY | `/lecture` |
| GENERAL_STUDY | `/ask` or `/help` |

## Data sources (per workflow)
- Telegram file download (PDF/text)
- Gmail (academic emails)
- Google Drive (study folder)
- Notion student tasks DB
- OpenAI (all responses, 4-section format)

## Files
- `workflows/00-main-router-workflow.json`
- `workflows/student/01-pdf-summary.json` … `08-general-ask.json`
