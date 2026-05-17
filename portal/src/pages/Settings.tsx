import { useState } from 'react';
import { Card, Button } from '../components/ui';
import { getSettings, saveSettings } from '../lib/store';

export function Settings() {
  const [settings, setSettings] = useState(getSettings());
  const [saved, setSaved] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="mt-1 text-zinc-400">Portal display + n8n reference (secrets stay in n8n only).</p>
      </div>
      <Card className="space-y-4 max-w-lg">
        <label className="block text-sm text-zinc-400">Notion Users Database ID</label>
        <input
          value={settings.notionUsersDbId}
          onChange={(e) => setSettings({ ...settings, notionUsersDbId: e.target.value })}
          className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white font-mono text-sm"
          placeholder="paste from Notion URL"
        />
        <label className="block text-sm text-zinc-400">Telegram bot username</label>
        <input
          value={settings.telegramBotName}
          onChange={(e) => setSettings({ ...settings, telegramBotName: e.target.value })}
          className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white"
        />
        <Button
          onClick={() => {
            saveSettings(settings);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
          }}
        >
          {saved ? 'Saved' : 'Save'}
        </Button>
      </Card>
      <Card>
        <h2 className="font-semibold text-white mb-2">n8n environment (required)</h2>
        <ul className="text-sm text-zinc-400 space-y-1 font-mono">
          <li>TELEGRAM_BOT_TOKEN</li>
          <li>GEMINI_API_KEY</li>
          <li>NOTION_API_KEY</li>
          <li>NOTION_USERS_DATABASE_ID</li>
          <li>NOTION_STUDENT_DATABASE_ID (study plan / deadlines)</li>
          <li>GMAIL_ACCESS_TOKEN (optional)</li>
        </ul>
        <p className="text-xs text-zinc-500 mt-3">See repo: docs/N8N-ENV-SETUP.md</p>
      </Card>
      <Card>
        <h2 className="font-semibold text-white mb-2">Demo mode (no Notion)</h2>
        <p className="text-sm text-zinc-400">In n8n set <code className="text-violet-300">AIVURA_DEMO_MODE=true</code> and optional <code className="text-violet-300">DEMO_ALLOWED_CHAT_IDS</code> (comma-separated). Empty allowlist = any Chat ID works.</p>
      </Card>
      <Card>
        <h2 className="font-semibold text-white mb-2">Notion Users DB properties</h2>
        <ul className="text-sm text-zinc-400 space-y-1">
          <li>• Name (title)</li>
          <li>• Telegram Chat ID (rich text)</li>
          <li>• Role (rich text) → always <code className="text-violet-300">student</code></li>
          <li>• Active (checkbox)</li>
        </ul>
      </Card>
    </div>
  );
}
