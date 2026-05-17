/** Aivura = university students only */
export const STUDENT_WORKFLOWS = [
  { id: 'summary', file: '01-pdf-summary.json', name: 'PDF / Document Summary', cmd: '/summary', emoji: '📄', desc: 'Send PDF + caption or /summary' },
  { id: 'mcq', file: '02-generate-mcq.json', name: 'Generate MCQs', cmd: '/mcq', emoji: '❓', desc: 'MCQs from topic or notes' },
  { id: 'submit', file: '03-submission-answer.json', name: 'Submission Answer', cmd: '/submit', emoji: '✍️', desc: 'Draft assignment answer structure' },
  { id: 'studyplan', file: '04-study-plan.json', name: 'Study Plan', cmd: '/studyplan', emoji: '📅', desc: 'Multi-day study schedule' },
  { id: 'deadlines', file: '05-deadlines.json', name: 'Deadlines', cmd: '/deadlines', emoji: '⏰', desc: 'Assignments & due dates' },
  { id: 'viva', file: '06-viva-prep.json', name: 'Viva Prep', cmd: '/viva', emoji: '🎤', desc: 'Viva questions + model answers' },
  { id: 'lecture', file: '07-lecture-summary.json', name: 'Lecture Summary', cmd: '/lecture', emoji: '📚', desc: 'Summarize lecture notes' },
  { id: 'flashcards', file: '09-flashcards.json', name: 'Flashcards', cmd: '/flashcards', emoji: '🃏', desc: 'Revision flashcards' },
  { id: 'today', file: '10-today.json', name: 'Today Plan', cmd: '/today', emoji: '📌', desc: 'Next few hours study plan' },
  { id: 'simple', file: '11-simple.json', name: 'Explain Simple', cmd: '/simple', emoji: '💡', desc: 'Hard topic in easy words' },
  { id: 'ask', file: '08-general-ask.json', name: 'Ask Anything', cmd: '/ask', emoji: '💬', desc: 'General study help' },
];

export const BOT_COMMANDS = [
  { cmd: '/help', desc: 'Show all commands' },
  ...STUDENT_WORKFLOWS.map((w) => ({ cmd: w.cmd, desc: w.desc })),
];
