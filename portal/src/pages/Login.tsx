import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Lock } from 'lucide-react';
import { adminLogin } from '../lib/auth';

export function Login() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminLogin(password)) {
      navigate('/');
    } else {
      setError('Invalid admin password');
    }
  };

  return (
    <div className="mesh-bg flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="glass w-full max-w-md rounded-3xl p-8">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600">
            <Bot className="h-7 w-7 text-white" />
          </div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl text-white">Aivura Admin</h1>
          <p className="mt-2 text-sm text-zinc-400">Add university students by Telegram Chat ID. Students use the bot only.</p>
        </div>
        <label className="mb-2 block text-sm text-zinc-400">Admin password</label>
        <div className="relative mb-4">
          <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black/40 py-3 pl-10 pr-4 text-white"
            placeholder="Enter admin password"
          />
        </div>
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <button type="submit" className="w-full rounded-xl bg-violet-600 py-2.5 font-medium text-white hover:bg-violet-500">
          Sign in
        </button>
        <p className="mt-6 text-center text-xs text-zinc-500">No user signup · Telegram bot only for end users</p>
      </form>
    </div>
  );
}
