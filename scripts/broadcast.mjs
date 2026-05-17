/**
 * Send a Telegram message to all chat IDs in an export file or CLI list.
 * Usage:
 *   node scripts/broadcast.mjs --message "Exam tomorrow 9am"
 *   node scripts/broadcast.mjs --file aivura-students-notion.json --message "Hello"
 *   node scripts/broadcast.mjs --ids 123,456 --message "Hi"
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

function loadEnv() {
  const p = path.join(ROOT, '.env');
  if (!fs.existsSync(p)) return {};
  const out = {};
  for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const i = t.indexOf('=');
    if (i > 0) out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return out;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { message: '', file: '', ids: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--message') opts.message = args[++i] || '';
    else if (args[i] === '--file') opts.file = args[++i] || '';
    else if (args[i] === '--ids') opts.ids = (args[++i] || '').split(',').map((s) => s.trim()).filter(Boolean);
  }
  return opts;
}

function idsFromFile(filePath) {
  const raw = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const list = Array.isArray(raw) ? raw : [raw];
  return list
    .map((r) => r['Telegram Chat ID'] || r.telegramChatId || r.chat_id)
    .filter(Boolean)
    .map(String);
}

const env = loadEnv();
const token = env.TELEGRAM_BOT_TOKEN;
const { message, file, ids: cliIds } = parseArgs();

if (!token) {
  console.error('Missing TELEGRAM_BOT_TOKEN in .env');
  process.exit(1);
}
if (!message.trim()) {
  console.error('Usage: node scripts/broadcast.mjs --message "Your text" [--file export.json | --ids 1,2,3]');
  process.exit(1);
}

let ids = cliIds;
if (file) ids = [...new Set([...ids, ...idsFromFile(path.resolve(file))])];
if (!ids.length) {
  console.error('No chat IDs. Use --ids or --file with exported students JSON.');
  process.exit(1);
}

console.log(`Broadcasting to ${ids.length} student(s)…\n`);

for (const chatId of ids) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: message }),
    });
    const data = await res.json();
    console.log(data.ok ? `✓ ${chatId}` : `✗ ${chatId}: ${data.description}`);
    await new Promise((r) => setTimeout(r, 350));
  } catch (e) {
    console.log(`✗ ${chatId}: ${e.message}`);
  }
}

console.log('\nDone.');
