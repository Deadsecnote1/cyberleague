import { Users, GraduationCap, MessageSquare, Bot, ExternalLink, CheckCircle2, Circle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, StatCard } from '../components/ui';
import { STUDENT_WORKFLOWS } from '../data/roles';
import { getUsers, getActivity, getSettings } from '../lib/store';

const SETUP = [
  { label: 'Add student + Chat ID in portal', key: 'users' },
  { label: 'Export → Notion Users DB', key: 'export' },
  { label: 'n8n: env vars + import 11 workflows', key: 'n8n' },
  { label: 'Activate router + test bot', key: 'test' },
];

export function Dashboard() {
  const users = getUsers().filter((u) => u.active);
  const allUsers = getUsers();
  const activity = getActivity();
  const { telegramBotName } = getSettings();
  const bot = telegramBotName.startsWith('@') ? telegramBotName : `@${telegramBotName}`;
  const botUrl = `https://t.me/${bot.replace('@', '')}`;

  const setupDone: Record<string, boolean> = {
    users: allUsers.some((u) => u.active && u.telegramChatId),
    export: allUsers.length > 0,
    n8n: false,
    test: false,
  };

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">Aivura Students</h1>
          <p className="mt-2 text-zinc-400">Telegram bot for university students. Admin adds Chat IDs here.</p>
        </div>
        <a
          href={botUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-xl bg-violet-600/20 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-600/30"
        >
          <Bot className="h-4 w-4" />
          Open {bot}
          <ExternalLink className="h-3.5 w-3.5 opacity-60" />
        </a>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Active students" value={users.length} icon={<Users className="h-5 w-5" />} />
        <StatCard label="n8n workflows" value={11} icon={<GraduationCap className="h-5 w-5" />} />
        <StatCard label="Activity" value={activity.length} icon={<MessageSquare className="h-5 w-5" />} />
        <StatCard label="Channel" value="Telegram" icon={<Bot className="h-5 w-5" />} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 font-semibold text-white">Setup checklist</h2>
          <ul className="space-y-3">
            {SETUP.map((s) => (
              <li key={s.key} className="flex items-start gap-3 text-sm text-zinc-400">
                {setupDone[s.key] ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                ) : (
                  <Circle className="mt-0.5 h-4 w-4 shrink-0 text-zinc-600" />
                )}
                {s.label}
              </li>
            ))}
          </ul>
          <Link to="/workflows" className="mt-4 inline-block text-sm text-violet-400 hover:text-violet-300">
            n8n workflow files →
          </Link>
        </Card>

        <Card>
          <h2 className="mb-4 font-semibold text-white">Student commands</h2>
          <div className="grid gap-2 sm:grid-cols-2 max-h-64 overflow-y-auto">
            {STUDENT_WORKFLOWS.map((w) => (
              <div key={w.id} className="rounded-xl bg-white/3 p-3">
                <span className="mr-1">{w.emoji}</span>
                <code className="text-violet-300 text-xs">{w.cmd}</code>
                <p className="mt-1 text-xs text-zinc-500">{w.desc}</p>
              </div>
            ))}
          </div>
          <Link to="/users" className="mt-4 inline-block text-sm text-violet-400 hover:text-violet-300">
            Add student →
          </Link>
        </Card>
      </div>
    </div>
  );
}
