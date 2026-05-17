import { Card, Badge } from '../components/ui';
import { getActivity } from '../lib/store';

export function Activity() {
  const logs = getActivity();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Activity Log</h1>
        <p className="mt-1 text-zinc-400">Telegram bot events — registered users and denied access attempts.</p>
      </div>
      <Card className="divide-y divide-white/5 p-0">
        {logs.map((a) => (
          <div key={a.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-zinc-200">{a.preview}</p>
              <p className="mt-1 text-xs text-zinc-500">{a.user} · {a.intent} · {new Date(a.time).toLocaleString()}</p>
            </div>
            <Badge tone={a.status === 'success' ? 'success' : a.status === 'denied' ? 'warn' : 'default'}>{a.status}</Badge>
          </div>
        ))}
      </Card>
    </div>
  );
}
