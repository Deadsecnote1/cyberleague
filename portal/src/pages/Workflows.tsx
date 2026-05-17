import { Card } from '../components/ui';
import { STUDENT_WORKFLOWS } from '../data/roles';

export function Workflows() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">n8n Workflows</h1>
        <p className="text-zinc-400 mt-1">Router + 11 separate student workflows (one feature each)</p>
      </div>
      <Card>
        <h3 className="font-semibold text-white">Main Router</h3>
        <code className="text-xs text-violet-300">workflows/00-main-router-workflow.json</code>
        <p className="text-sm text-zinc-500 mt-2">Telegram → chat_id lookup → intent → run student workflow → reply</p>
      </Card>
      <Card>
        <h3 className="font-semibold text-white">Student workflows</h3>
        <p className="text-sm text-zinc-500 mb-3">
          Import from <code className="text-violet-300">workflows/student/</code>
        </p>
        <ul className="space-y-2 text-sm text-zinc-400">
          {STUDENT_WORKFLOWS.map((w) => (
            <li key={w.id}>
              {w.emoji} <strong className="text-zinc-300">{w.name}</strong> —{' '}
              <code className="text-xs text-violet-300/80">{w.file}</code> — {w.cmd}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

