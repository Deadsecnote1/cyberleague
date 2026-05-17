import { useState } from 'react';
import { Card, Button } from '../components/ui';
import { getUsers } from '../lib/store';
import { Megaphone, Send } from 'lucide-react';

export function Broadcast() {
  const active = getUsers().filter((u) => u.active && u.telegramChatId);
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const token = import.meta.env.VITE_TELEGRAM_BOT_TOKEN as string | undefined;

  const sendFromPortal = async () => {
    if (!token) {
      setStatus('Add VITE_TELEGRAM_BOT_TOKEN to portal/.env (local admin only).');
      return;
    }
    if (!message.trim() || !active.length) return;
    setSending(true);
    setStatus(null);
    let ok = 0;
    for (const u of active) {
      try {
        const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: u.telegramChatId, text: message.trim() }),
        });
        const data = await res.json();
        if (data.ok) ok++;
        await new Promise((r) => setTimeout(r, 400));
      } catch {
        /* skip */
      }
    }
    setStatus(`Sent to ${ok} / ${active.length} students.`);
    setSending(false);
  };

  const cliHint = `node scripts/broadcast.mjs --message "${message.replace(/"/g, '\\"')}" --ids ${active.map((u) => u.telegramChatId).join(',')}`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Broadcast</h1>
        <p className="text-sm text-zinc-400 mt-1">Message all active students on @Aivura_bot</p>
      </div>

      <Card className="space-y-4 max-w-xl">
        <label className="text-sm text-zinc-400">Message</label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          placeholder="Exams start Monday. Good luck!"
          className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white resize-none"
        />
        <p className="text-xs text-zinc-500">{active.length} active student(s) in portal</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={sendFromPortal} disabled={sending || !message.trim() || !active.length}>
            <Send className="h-4 w-4" /> {sending ? 'Sending…' : 'Send from portal'}
          </Button>
        </div>
        {status && <p className="text-sm text-violet-300">{status}</p>}
      </Card>

      <Card>
        <h2 className="font-semibold text-white mb-2 flex items-center gap-2">
          <Megaphone className="h-4 w-4" /> Or use CLI (safer)
        </h2>
        <p className="text-sm text-zinc-400 mb-2">Export students from Users, then:</p>
        <code className="block text-xs text-violet-300 bg-black/40 p-3 rounded-xl break-all">{cliHint}</code>
      </Card>
    </div>
  );
}
