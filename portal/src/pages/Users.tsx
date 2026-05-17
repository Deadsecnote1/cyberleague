import { useState } from 'react';
import { Card, Badge, Button } from '../components/ui';
import { getUsers, addUser, deleteUser, updateUser, exportUsersForNotion, type UserRecord } from '../lib/store';
import { Plus, Download, Trash2, Copy, Check } from 'lucide-react';

export function Users() {
  const [users, setUsers] = useState<UserRecord[]>(getUsers);
  const [showForm, setShowForm] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', telegramChatId: '', studentId: '', department: '', active: true });

  const refresh = () => setUsers(getUsers());

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.telegramChatId) return;
    addUser(form);
    refresh();
    setForm({ name: '', telegramChatId: '', studentId: '', department: '', active: true });
    setShowForm(false);
  };

  const copyChatId = async (id: string, chatId: string) => {
    await navigator.clipboard.writeText(chatId);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const exportJson = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(exportUsersForNotion(), null, 2)], { type: 'application/json' }));
    a.download = 'aivura-students-notion.json';
    a.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Students</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Add Telegram Chat ID → export → paste into Notion Users DB. Bot blocks unknown IDs.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportJson} disabled={!users.length}>
            <Download className="h-4 w-4" /> Export for Notion
          </Button>
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4" /> Add student
          </Button>
        </div>
      </div>

      {showForm && (
        <Card>
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
            <input required placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white" />
            <input required placeholder="Telegram Chat ID (from @userinfobot)" value={form.telegramChatId} onChange={(e) => setForm({ ...form, telegramChatId: e.target.value.replace(/\s/g, '') })} className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white font-mono" />
            <input placeholder="Student ID" value={form.studentId} onChange={(e) => setForm({ ...form, studentId: e.target.value })} className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white" />
            <input placeholder="Department / Course" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className="rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-white" />
            <label className="flex items-center gap-2 text-sm text-zinc-300 sm:col-span-2">
              <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Active (can use bot)
            </label>
            <Button type="submit" className="sm:col-span-2">Save student</Button>
          </form>
        </Card>
      )}

      {!users.length ? (
        <Card className="text-center py-12">
          <p className="text-zinc-400">No students yet.</p>
          <p className="text-sm text-zinc-500 mt-2">Add your first student, then export to Notion.</p>
          <Button className="mt-4" onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4" /> Add student
          </Button>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-xs uppercase text-zinc-500 bg-white/3">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Chat ID</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 w-28"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-white/5">
                  <td className="px-4 py-3 text-zinc-200">{u.name}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400">{u.telegramChatId}</td>
                  <td className="px-4 py-3 text-zinc-500">{u.department || '—'}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => { updateUser(u.id, { active: !u.active }); refresh(); }}
                      title="Toggle active"
                    >
                      <Badge tone={u.active ? 'success' : 'warn'}>{u.active ? 'Active' : 'Off'}</Badge>
                    </button>
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <button type="button" onClick={() => copyChatId(u.id, u.telegramChatId)} className="text-zinc-500 hover:text-violet-300" title="Copy Chat ID">
                      {copiedId === u.id ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                    </button>
                    <button type="button" onClick={() => { deleteUser(u.id); refresh(); }} className="text-zinc-500 hover:text-red-400">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
