/**
 * Quick sanity check — reads root .env (gitignored).
 * Usage: node scripts/verify-setup.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const envPath = path.join(ROOT, '.env');

function loadEnv() {
  if (!fs.existsSync(envPath)) return {};
  const out = {};
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const i = t.indexOf('=');
    if (i > 0) out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return out;
}

const env = loadEnv();
const checks = [
  { key: 'TELEGRAM_BOT_TOKEN', label: 'Telegram bot' },
  { key: 'GEMINI_API_KEY', label: 'Gemini' },
  { key: 'NOTION_API_KEY', label: 'Notion' },
  { key: 'NOTION_USERS_DATABASE_ID', label: 'Notion Users DB' },
];

console.log('\nAivura setup check\n');

for (const { key, label } of checks) {
  const ok = Boolean(env[key]);
  console.log(`${ok ? '✓' : '✗'} ${label} (${key})`);
}

const wfDir = path.join(ROOT, 'workflows', 'student');
const wfCount = fs.existsSync(wfDir) ? fs.readdirSync(wfDir).filter((f) => f.endsWith('.json')).length : 0;
console.log(`${wfCount === 11 ? '✓' : '✗'} Student workflows (${wfCount}/11)`);
console.log(`${fs.existsSync(path.join(ROOT, 'workflows', '00-main-router-workflow.json')) ? '✓' : '✗'} Router workflow`);

if (env.TELEGRAM_BOT_TOKEN) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getMe`);
    const data = await res.json();
    if (data.ok) console.log(`✓ Bot live: @${data.result.username}`);
    else console.log(`✗ Telegram API: ${data.description}`);
  } catch (e) {
    console.log(`✗ Telegram ping failed: ${e.message}`);
  }
}

console.log('\nNext: import workflows in n8n → activate router → test @Aivura_bot\n');
