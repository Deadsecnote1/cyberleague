/**
 * Build Aivura student Telegram bot:
 * - 1 router workflow
 * - 11 separate student workflows (no mixing)
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const STUDENT_DIR = path.join(ROOT, 'workflows', 'student');
const gToken = "={{ $env.GMAIL_ACCESS_TOKEN || $env.GOOGLE_ACCESS_TOKEN }}";
const GEMINI_MODEL = 'gemini-2.0-flash';
const GEMINI_URL = `=https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key={{ $env.GEMINI_API_KEY }}`;
const GEMINI_REPLY = `r?.candidates?.[0]?.content?.parts?.[0]?.text?.trim()`;

const FEATURES = [
  {
    file: '01-pdf-summary',
    name: 'Aivura Student – PDF Summary',
    intent: 'DOCUMENT_SUMMARY',
    cmd: '/summary',
    emoji: '📄',
    desc: 'Summarize PDF or document from Telegram',
    needsPdf: true,
    system: 'Summarize uploaded PDF/document for a university student. Extract key points, definitions, formulas, exam tips.',
    tools: ['telegram_file'],
  },
  {
    file: '02-generate-mcq',
    name: 'Aivura Student – Generate MCQ',
    intent: 'GENERATE_MCQ',
    cmd: '/mcq',
    emoji: '❓',
    desc: 'Generate multiple-choice questions with answers',
    system: 'Create 5-10 MCQs with 4 options each. Put correct answers in section 4.',
    tools: [],
  },
  {
    file: '03-submission-answer',
    name: 'Aivura Student – Submission Answer',
    intent: 'SUBMISSION_ANSWER',
    cmd: '/submit',
    emoji: '✍️',
    desc: 'Draft assignment submission structure',
    system: 'Draft a structured assignment answer: introduction, main body, conclusion. Study aid only—student must verify.',
    tools: [],
  },
  {
    file: '04-study-plan',
    name: 'Aivura Student – Study Plan',
    intent: 'STUDY_PLAN',
    cmd: '/studyplan',
    emoji: '📅',
    desc: 'Multi-day study schedule',
    system: 'Create a realistic study plan with daily blocks, priorities, and breaks. Use tasks/deadlines if provided.',
    tools: ['gmail', 'notion'],
  },
  {
    file: '05-deadlines',
    name: 'Aivura Student – Deadlines',
    intent: 'ASSIGNMENT_DEADLINES',
    cmd: '/deadlines',
    emoji: '⏰',
    desc: 'Assignments and urgent due dates',
    system: 'List upcoming deadlines and urgent academic tasks clearly by date.',
    tools: ['gmail', 'notion'],
  },
  {
    file: '06-viva-prep',
    name: 'Aivura Student – Viva Prep',
    intent: 'VIVA_PREP',
    cmd: '/viva',
    emoji: '🎤',
    desc: 'Viva questions and model answers',
    system: 'Generate 8-12 likely viva questions with short model answers.',
    tools: [],
  },
  {
    file: '07-lecture-summary',
    name: 'Aivura Student – Lecture Summary',
    intent: 'LECTURE_SUMMARY',
    cmd: '/lecture',
    emoji: '📚',
    desc: 'Summarize lecture notes',
    needsPdf: true,
    system: 'Summarize lecture notes emphasizing structure, key concepts, and revision bullets.',
    tools: ['telegram_file'],
  },
  {
    file: '09-flashcards',
    name: 'Aivura Student – Flashcards',
    intent: 'FLASHCARDS',
    cmd: '/flashcards',
    emoji: '🃏',
    desc: 'Revision flashcards from topic or notes',
    system: 'Create 8-15 flashcards. Format each as Front: question/term | Back: short answer. Put full card list in section 4.',
    tools: [],
  },
  {
    file: '10-today',
    name: 'Aivura Student – Today Plan',
    intent: 'TODAY_PLAN',
    cmd: '/today',
    emoji: '📌',
    desc: 'Focused plan for the next few hours today',
    system: 'Create a realistic plan for TODAY only: next 3-6 hours in time blocks. Prioritize urgent tasks and exams. Use notion_tasks if provided.',
    tools: ['notion'],
  },
  {
    file: '11-simple',
    name: 'Aivura Student – Explain Simple',
    intent: 'EXPLAIN_SIMPLE',
    cmd: '/simple',
    emoji: '💡',
    desc: 'Explain a hard topic in simple words',
    system: 'Explain the topic like the student is 15 years old. Use short sentences, one analogy, and 3 bullet takeaways. No jargon without definition.',
    tools: [],
  },
  {
    file: '08-general-ask',
    name: 'Aivura Student – General Ask',
    intent: 'GENERAL_STUDY',
    cmd: '/ask',
    emoji: '💬',
    desc: 'General study questions and /help',
    system: 'Answer the student clearly. If they said /help, list commands: /summary /mcq /submit /studyplan /deadlines /viva /lecture /flashcards /today /simple /ask',
    tools: [],
  },
];

const pdfCode = `const base = $('01 – Input').first().json;
const apiErrors = [];
let document_content = '';
const geminiKey = $env.GEMINI_API_KEY || '';
const GEMINI_MODEL = '${GEMINI_MODEL}';
if (base.has_document && base.file_id) {
  const token = $env.TELEGRAM_BOT_TOKEN;
  try {
    const info = await this.helpers.httpRequest({ method: 'GET', url: 'https://api.telegram.org/bot' + token + '/getFile', qs: { file_id: base.file_id }, json: true });
    const fp = info?.result?.file_path;
    if (fp) {
      const bin = await this.helpers.httpRequest({ method: 'GET', url: 'https://api.telegram.org/file/bot' + token + '/' + fp, encoding: 'arraybuffer', returnFullResponse: true });
      const buf = Buffer.from(bin.body || bin);
      const mime = base.mime_type || 'application/octet-stream';
      const fname = base.file_name || 'document';
      if (mime.includes('text') || fname.endsWith('.txt')) {
        document_content = buf.toString('utf8').slice(0, 12000);
      } else if (geminiKey && buf.length > 0 && buf.length < 4200000) {
        const b64 = buf.toString('base64');
        let mimeType = 'application/pdf';
        if (mime.includes('pdf')) mimeType = 'application/pdf';
        else if (mime.startsWith('image/')) mimeType = mime;
        else if (fname.match(/\\.(png|jpg|jpeg|webp)$/i)) mimeType = 'image/jpeg';
        const gr = await this.helpers.httpRequest({
          method: 'POST',
          url: 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent?key=' + geminiKey,
          body: {
            contents: [{ parts: [
              { inline_data: { mime_type: mimeType, data: b64 } },
              { text: 'Extract all readable text and main headings from this academic file (' + fname + '). Plain text only, max 8000 characters.' }
            ]}],
            generationConfig: { temperature: 0.2, maxOutputTokens: 8192 }
          },
          json: true,
          timeout: 90000
        });
        document_content = (gr?.candidates?.[0]?.content?.parts?.[0]?.text || '').slice(0, 12000);
        if (!document_content.trim()) apiErrors.push('Gemini vision: no text extracted');
      } else {
        document_content = (base.user_message || '') + ' [File: ' + fname + ' — too large or missing GEMINI_API_KEY for vision]';
        apiErrors.push('Vision skipped');
      }
    }
  } catch (e) { apiErrors.push('File: ' + e.message); document_content = base.user_message || ''; }
} else {
  document_content = base.user_message || '';
  if (base.has_document) apiErrors.push('Could not read file');
}
return [{ json: { ...base, document_content, api_errors: apiErrors } }];`;

const gmailNode = {
  parameters: {
    method: 'GET', url: 'https://gmail.googleapis.com/gmail/v1/users/me/messages',
    sendQuery: true,
    queryParameters: { parameters: [
      { name: 'maxResults', value: '6' },
      { name: 'q', value: 'newer_than:14d (assignment OR deadline OR exam OR homework OR course)' },
    ]},
    sendHeaders: true,
    headerParameters: { parameters: [{ name: 'Authorization', value: gToken }] },
    options: { timeout: 20000 },
  },
  type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, continueOnFail: true, alwaysOutputData: true,
};

const notionNode = {
  parameters: {
    method: 'POST',
    url: '=https://api.notion.com/v1/databases/{{ $env.NOTION_STUDENT_DATABASE_ID }}/query',
    sendHeaders: true,
    headerParameters: {
      parameters: [
        { name: 'Authorization', value: '=Bearer {{ $env.NOTION_API_KEY }}' },
        { name: 'Notion-Version', value: '2022-06-28' },
        { name: 'Content-Type', value: 'application/json' },
      ],
    },
    sendBody: true, specifyBody: 'json', jsonBody: '={ "page_size": 12 }',
    options: { timeout: 20000 },
  },
  type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, continueOnFail: true, alwaysOutputData: true,
};

function buildContextCode(f) {
  return `const item = $input.first().json;
const apiErrors = [...(item.api_errors || [])];
const ctx = { intent: '${f.intent}' };
${f.needsPdf ? 'ctx.document_content = item.document_content || item.user_message || "";' : ''}
${f.tools.includes('gmail') ? `try {
  const g = $('02 – Gmail').first().json;
  const token = $env.GMAIL_ACCESS_TOKEN || $env.GOOGLE_ACCESS_TOKEN || '';
  ctx.gmail = [];
  if (g?.messages && token) {
    for (const m of g.messages.slice(0, 4)) {
      const d = await this.helpers.httpRequest({ method: 'GET', url: 'https://gmail.googleapis.com/gmail/v1/users/me/messages/' + m.id, qs: { format: 'metadata', metadataHeaders: ['Subject','Date'] }, headers: { Authorization: 'Bearer ' + token }, json: true });
      const h = (n) => (d.payload?.headers||[]).find(x=>x.name===n)?.value||'';
      ctx.gmail.push({ subject: h('Subject'), date: h('Date'), snippet: d.snippet });
    }
  }
} catch(e) { apiErrors.push('Gmail:'+e.message); }` : ''}
${f.tools.includes('notion') ? `try {
  const n = $('${f.tools.includes('gmail') ? '03 – Notion' : '02 – Notion'}').first().json;
  ctx.notion_tasks = (n.results||[]).map(p => ({ title: p.properties?.Name?.title?.[0]?.plain_text || 'Task', due: p.properties?.Due?.date?.start }));
} catch(e) { apiErrors.push('Notion:'+e.message); }` : ''}
return [{ json: { ...item, collected_context: ctx, api_errors: apiErrors } }];`;
}

function buildStudentWorkflowClean(f) {
  const nodes = [
    { parameters: {}, id: 't', name: '00 – Trigger', type: 'n8n-nodes-base.executeWorkflowTrigger', typeVersion: 1.1, position: [0, 300] },
    {
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [
            { id: 'chat_id', name: 'chat_id', value: '={{ $json.chat_id }}', type: 'number' },
            { id: 'username', name: 'username', value: '={{ $json.username || "Student" }}', type: 'string' },
            { id: 'user_message', name: 'user_message', value: '={{ $json.user_message }}', type: 'string' },
            { id: 'has_document', name: 'has_document', value: '={{ $json.has_document || false }}', type: 'boolean' },
            { id: 'file_id', name: 'file_id', value: '={{ $json.file_id || "" }}', type: 'string' },
            { id: 'file_name', name: 'file_name', value: '={{ $json.file_name || "" }}', type: 'string' },
            { id: 'mime_type', name: 'mime_type', value: '={{ $json.mime_type || "" }}', type: 'string' },
          ],
        },
      },
      id: 'in', name: '01 – Input', type: 'n8n-nodes-base.set', typeVersion: 3.4, position: [200, 300],
    },
  ];
  const conn = { '00 – Trigger': { main: [[{ node: '01 – Input', type: 'main', index: 0 }]] } };
  let prev = '01 – Input';
  let x = 420;

  if (f.needsPdf) {
    nodes.push({ parameters: { jsCode: pdfCode }, id: 'pdf', name: '02 – Get Document', type: 'n8n-nodes-base.code', typeVersion: 2, position: [x, 300] });
    conn[prev] = { main: [[{ node: '02 – Get Document', type: 'main', index: 0 }]] };
    prev = '02 – Get Document';
    x += 220;
  }

  const parallel = [];
  if (f.tools.includes('gmail')) {
    nodes.push({ ...gmailNode, id: 'gm', name: '02 – Gmail', position: [x, 160] });
    parallel.push({ node: '02 – Gmail', type: 'main', index: 0 });
  }
  if (f.tools.includes('notion')) {
    const nn = f.tools.includes('gmail') ? '03 – Notion' : '02 – Notion';
    nodes.push({ ...notionNode, id: 'nt', name: nn, position: [x, 440] });
    parallel.push({ node: nn, type: 'main', index: 0 });
  }

  const ctxName = '03 – Build Context';
  const ctxJs = buildContextCode(f);
  nodes.push({ parameters: { jsCode: ctxJs }, id: 'ctx', name: ctxName, type: 'n8n-nodes-base.code', typeVersion: 2, position: [x + 220, 300] });

  if (parallel.length) {
    conn[prev] = { main: [parallel] };
    parallel.forEach((p) => { conn[p.node] = { main: [[{ node: ctxName, type: 'main', index: 0 }]] }; });
  } else {
    conn[prev] = { main: [[{ node: ctxName, type: 'main', index: 0 }]] };
  }

  const promptJs = `const j = $input.first().json;
return [{ json: { ...j, gemini_request: {
  systemInstruction: { parts: [{ text: ${JSON.stringify(f.system + ' Always use: ## 1. Quick Summary ## 2. Important Findings ## 3. Suggested Next Actions ## 4. Draft / Plan / Checklist')} }] },
  contents: [{ role: 'user', parts: [{ text: JSON.stringify({ message: j.user_message, context: j.collected_context, errors: j.api_errors }) }] }],
  generationConfig: { temperature: 0.4 },
} } }];`;

  nodes.push({ parameters: { jsCode: promptJs }, id: 'pr', name: '04 – AI Prompt', type: 'n8n-nodes-base.code', typeVersion: 2, position: [x + 440, 300] });
  conn[ctxName] = { main: [[{ node: '04 – AI Prompt', type: 'main', index: 0 }]] };

  nodes.push({
    parameters: {
      method: 'POST',
      url: GEMINI_URL,
      sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
      sendBody: true,
      specifyBody: 'json',
      jsonBody: '={{ JSON.stringify($json.gemini_request) }}',
      options: { timeout: 60000 },
    },
    id: 'ai',
    name: '05 – Gemini',
    type: 'n8n-nodes-base.httpRequest',
    typeVersion: 4.2,
    position: [x + 660, 300],
    continueOnFail: true,
    alwaysOutputData: true,
  });
  conn['04 – AI Prompt'] = { main: [[{ node: '05 – Gemini', type: 'main', index: 0 }]] };

  nodes.push({
    parameters: {
      jsCode: `const m = $('04 – AI Prompt').first().json;
const r = $input.first().json;
let reply = ${GEMINI_REPLY} || '## 1. Quick Summary\\nService error.\\n\\n## 2. Important Findings\\n' + (r?.error?.message || 'Try again') + '\\n\\n## 3. Suggested Next Actions\\n- Retry\\n\\n## 4. Draft / Plan / Checklist\\n- [ ]';
if (reply.length > 3900) reply = reply.slice(0, 3900) + '…';
return [{ json: { chat_id: m.chat_id, reply_text: reply, intent: '${f.intent}' } }];`,
    },
    id: 'fmt',
    name: '06 – Format Reply',
    type: 'n8n-nodes-base.code',
    typeVersion: 2,
    position: [x + 880, 300],
  });
  conn['05 – Gemini'] = { main: [[{ node: '06 – Format Reply', type: 'main', index: 0 }]] };

  nodes.push({
    parameters: { mode: 'manual', assignments: { assignments: [
      { id: 'reply_text', name: 'reply_text', value: '={{ $json.reply_text }}', type: 'string' },
      { id: 'chat_id', name: 'chat_id', value: '={{ $json.chat_id }}', type: 'number' },
      { id: 'intent', name: 'intent', value: `=${f.intent}`, type: 'string' },
    ]}},
    id: 'ret', name: '07 – Return', type: 'n8n-nodes-base.set', typeVersion: 3.4, position: [x + 1100, 300],
  });
  conn['06 – Format Reply'] = { main: [[{ node: '07 – Return', type: 'main', index: 0 }]] };

  return { name: f.name, nodes, connections: conn, pinData: {}, settings: { executionOrder: 'v1' }, tags: [{ name: 'aivura' }, { name: f.file }], meta: { instanceId: `aivura-${f.file}` } };
}

function buildRouter() {
  const switchRules = FEATURES.map((f) => ({
    conditions: {
      options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
      conditions: [{ leftValue: '={{ $json.intent }}', rightValue: f.intent, operator: { type: 'string', operation: 'equals' } }],
      combinator: 'and',
    },
    renameOutput: true,
    outputKey: f.intent,
  }));

  const execNodes = FEATURES.map((f, i) => ({
    parameters: {
      workflowId: { __rl: true, mode: 'list', value: '', cachedResultName: f.name },
      workflowInputs: {
        mappingMode: 'defineBelow',
        value: {
          chat_id: '={{ $json.chat_id }}',
          username: '={{ $json.username }}',
          user_message: '={{ $json.user_message }}',
          has_document: '={{ $json.has_document }}',
          file_id: '={{ $json.file_id }}',
          file_name: '={{ $json.file_name }}',
          mime_type: '={{ $json.mime_type }}',
        },
      },
      options: { waitForSubWorkflow: true },
    },
    id: `ex-${f.file}`,
    name: `RUN – ${f.emoji} ${f.cmd}`,
    type: 'n8n-nodes-base.executeWorkflow',
    typeVersion: 1.2,
    position: [1700, 60 + i * 70],
    continueOnFail: true,
    alwaysOutputData: true,
  }));

  const lookupCode = `const base = $('02 – Extract').first().json;
const notion = $input.first().json;
let access_denied = true;
let deny_reason = 'Not registered. Admin must add your Telegram Chat ID in Aivura Portal.';
const demo = String($env.AIVURA_DEMO_MODE || '').toLowerCase() === 'true';
const allowList = String($env.DEMO_ALLOWED_CHAT_IDS || '').split(',').map(s => s.trim()).filter(Boolean);
const cid = String(base.chat_id);
if (demo) {
  if (!allowList.length || allowList.includes(cid)) access_denied = false;
  else deny_reason = 'Demo mode: Chat ID not in DEMO_ALLOWED_CHAT_IDS.';
} else if (notion?.results?.[0]?.properties?.Active?.checkbox === true) {
  access_denied = false;
}
return [{ json: { ...base, access_denied, deny_reason, demo_mode: demo } }];`;

  const parseIntent = `const p = $('04 – Lookup Student').first().json;
let intent = 'GENERAL_STUDY';
try {
  const raw = $('06 – Detect Intent').first().json?.candidates?.[0]?.content?.parts?.[0]?.text;
  const c = raw;
  if (c) intent = JSON.parse(c).user_intent || intent;
} catch (e) {}
const msg = (p.user_message || '').toLowerCase().trim();
const cmds = { '/summary':'DOCUMENT_SUMMARY','/mcq':'GENERATE_MCQ','/submit':'SUBMISSION_ANSWER','/studyplan':'STUDY_PLAN','/deadlines':'ASSIGNMENT_DEADLINES','/viva':'VIVA_PREP','/lecture':'LECTURE_SUMMARY','/flashcards':'FLASHCARDS','/today':'TODAY_PLAN','/simple':'EXPLAIN_SIMPLE','/ask':'GENERAL_STUDY','/help':'GENERAL_STUDY','/start':'GENERAL_STUDY' };
for (const [k,v] of Object.entries(cmds)) { if (msg === k || msg.startsWith(k + ' ')) { intent = v; break; } }
if (p.has_document && intent === 'GENERAL_STUDY') intent = 'DOCUMENT_SUMMARY';
return [{ json: { ...p, intent } }];`;

  const nodes = [
    { parameters: { updates: ['message'] }, id: 'r1', name: '01 – Telegram Trigger', type: 'n8n-nodes-base.telegramTrigger', typeVersion: 1.1, position: [0, 400], webhookId: 'aivura-bot' },
    {
      parameters: { mode: 'manual', assignments: { assignments: [
        { id: 'chat_id', name: 'chat_id', value: '={{ $json.message.chat.id }}', type: 'number' },
        { id: 'username', name: 'username', value: '={{ $json.message.from.username || $json.message.from.first_name }}', type: 'string' },
        { id: 'user_message', name: 'user_message', value: '={{ $json.message.text || $json.message.caption || "" }}', type: 'string' },
        { id: 'has_document', name: 'has_document', value: '={{ !!$json.message.document }}', type: 'boolean' },
        { id: 'file_id', name: 'file_id', value: '={{ $json.message.document?.file_id || "" }}', type: 'string' },
        { id: 'file_name', name: 'file_name', value: '={{ $json.message.document?.file_name || "" }}', type: 'string' },
        { id: 'mime_type', name: 'mime_type', value: '={{ $json.message.document?.mime_type || "" }}', type: 'string' },
      ]}},
      id: 'r2', name: '02 – Extract', type: 'n8n-nodes-base.set', typeVersion: 3.4, position: [220, 400],
    },
    {
      parameters: {
        method: 'POST',
        url: '=https://api.notion.com/v1/databases/{{ $env.NOTION_USERS_DATABASE_ID }}/query',
        sendHeaders: true,
        headerParameters: { parameters: [
          { name: 'Authorization', value: '=Bearer {{ $env.NOTION_API_KEY }}' },
          { name: 'Notion-Version', value: '2022-06-28' },
          { name: 'Content-Type', value: 'application/json' },
        ]},
        sendBody: true, specifyBody: 'json',
        jsonBody: '={{ JSON.stringify({ page_size: 1, filter: { property: "Telegram Chat ID", rich_text: { equals: String($json.chat_id) } } }) }}',
        options: { timeout: 15000 },
      },
      id: 'r3', name: '03 – Check Registered', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [440, 400],
      continueOnFail: true, alwaysOutputData: true,
    },
    { parameters: { jsCode: lookupCode }, id: 'r4', name: '04 – Lookup Student', type: 'n8n-nodes-base.code', typeVersion: 2, position: [660, 400] },
    {
      parameters: { conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: '={{ $json.access_denied }}', rightValue: true, operator: { type: 'boolean', operation: 'equals' } }], combinator: 'and' }},
      id: 'r5', name: '05 – Denied?', type: 'n8n-nodes-base.if', typeVersion: 2.2, position: [880, 400],
    },
    {
      parameters: {
        method: 'POST', url: '=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage',
        sendBody: true, specifyBody: 'json',
        jsonBody: '={\n  "chat_id": {{ $json.chat_id }},\n  "text": {{ JSON.stringify($json.deny_reason + "\\n\\n/help for commands") }}\n}',
      },
      id: 'r5a', name: '05a – Send Denied', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [1100, 280],
    },
    {
      parameters: {
        method: 'POST',
        url: GEMINI_URL,
        sendHeaders: true,
        headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
        sendBody: true,
        specifyBody: 'json',
        jsonBody:
          '={\n  "systemInstruction": { "parts": [{ "text": "Return JSON only with key user_intent. One of: DOCUMENT_SUMMARY, GENERATE_MCQ, SUBMISSION_ANSWER, STUDY_PLAN, ASSIGNMENT_DEADLINES, VIVA_PREP, LECTURE_SUMMARY, FLASHCARDS, TODAY_PLAN, EXPLAIN_SIMPLE, GENERAL_STUDY" }] },\n  "contents": [{ "role": "user", "parts": [{ "text": "msg: {{ $json.user_message }}\\nhasPdf: {{ $json.has_document }}" }] }],\n  "generationConfig": { "temperature": 0, "responseMimeType": "application/json" }\n}',
        options: { timeout: 25000 },
      },
      id: 'r6',
      name: '06 – Detect Intent',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.2,
      position: [1100, 520],
      continueOnFail: true,
      alwaysOutputData: true,
    },
    { parameters: { jsCode: parseIntent }, id: 'r7', name: '07 – Parse Intent', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1320, 520] },
    { parameters: { rules: { values: switchRules }, options: { fallbackOutput: 'extra', renameFallbackOutput: 'GENERAL' } }, id: 'r8', name: '08 – Route Workflow', type: 'n8n-nodes-base.switch', typeVersion: 3.2, position: [1540, 520] },
    ...execNodes,
    {
      parameters: {
        jsCode: `let reply = 'Error.'; let chat_id = $('07 – Parse Intent').first().json.chat_id;
for (const i of $input.all()) { if (i.json?.reply_text) { reply = i.json.reply_text; break; } }
return [{ json: { chat_id, reply_text: reply } }];`,
      },
      id: 'r9', name: '09 – Collect Reply', type: 'n8n-nodes-base.code', typeVersion: 2, position: [1980, 520],
    },
    {
      parameters: {
        method: 'POST', url: '=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage',
        sendBody: true, specifyBody: 'json',
        jsonBody: '={\n  "chat_id": {{ $json.chat_id }},\n  "text": {{ JSON.stringify($json.reply_text) }},\n  "parse_mode": "Markdown"\n}',
      },
      id: 'r10', name: '10 – Telegram Reply', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position: [2200, 520],
      continueOnFail: true, alwaysOutputData: true,
    },
  ];

  const conn = {
    '01 – Telegram Trigger': { main: [[{ node: '02 – Extract', type: 'main', index: 0 }]] },
    '02 – Extract': { main: [[{ node: '03 – Check Registered', type: 'main', index: 0 }]] },
    '03 – Check Registered': { main: [[{ node: '04 – Lookup Student', type: 'main', index: 0 }]] },
    '04 – Lookup Student': { main: [[{ node: '05 – Denied?', type: 'main', index: 0 }]] },
    '05 – Denied?': { main: [[{ node: '05a – Send Denied', type: 'main', index: 0 }], [{ node: '06 – Detect Intent', type: 'main', index: 0 }]] },
    '06 – Detect Intent': { main: [[{ node: '07 – Parse Intent', type: 'main', index: 0 }]] },
    '07 – Parse Intent': { main: [[{ node: '08 – Route Workflow', type: 'main', index: 0 }]] },
    '08 – Route Workflow': { main: FEATURES.map((f) => [{ node: `RUN – ${f.emoji} ${f.cmd}`, type: 'main', index: 0 }]) },
    '09 – Collect Reply': { main: [[{ node: '10 – Telegram Reply', type: 'main', index: 0 }]] },
  };

  FEATURES.forEach((f) => {
    conn[`RUN – ${f.emoji} ${f.cmd}`] = { main: [[{ node: '09 – Collect Reply', type: 'main', index: 0 }]] };
  });

  return { name: 'Aivura – Telegram Bot Router', nodes, connections: conn, pinData: {}, settings: { executionOrder: 'v1' }, tags: [{ name: 'aivura' }], meta: { instanceId: 'aivura-router-v4' } };
}

// --- run ---
fs.mkdirSync(STUDENT_DIR, { recursive: true });

for (const f of FEATURES) {
  const wf = buildStudentWorkflowClean(f);
  fs.writeFileSync(path.join(STUDENT_DIR, `${f.file}.json`), JSON.stringify(wf, null, 2));
  console.log('  student/', f.file + '.json');
}

fs.writeFileSync(path.join(ROOT, 'workflows', '00-main-router-workflow.json'), JSON.stringify(buildRouter(), null, 2));
console.log('  workflows/00-main-router-workflow.json');

const testMd = `# Telegram Tests\n\n| Command | Workflow file |\n|---------|---------------|\n${FEATURES.map((f) => `| ${f.cmd} | student/${f.file}.json |`).join('\n')}\n\n## PDF\nSend PDF with caption: Summarize chapter 2\n\n## Natural\n"Create 10 MCQs on binary search"\n`;
fs.writeFileSync(path.join(STUDENT_DIR, 'TELEGRAM-TESTS.md'), testMd);

// Remove old roles folder
const rolesDir = path.join(ROOT, 'roles');
if (fs.existsSync(rolesDir)) fs.rmSync(rolesDir, { recursive: true, force: true });

// Remove old build script
const old = path.join(ROOT, 'scripts', 'build-student-only.mjs');
if (fs.existsSync(old)) fs.unlinkSync(old);

console.log('Done. Removed roles/ folder.');
