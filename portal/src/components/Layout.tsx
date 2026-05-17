import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Activity, Workflow, Settings, Menu, Bot, LogOut, Megaphone } from 'lucide-react';
import { useState } from 'react';
import { adminLogout } from '../lib/auth';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/activity', label: 'Activity', icon: Activity },
  { to: '/workflows', label: 'n8n Workflows', icon: Workflow },
  { to: '/broadcast', label: 'Broadcast', icon: Megaphone },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const logout = () => {
    adminLogout();
    navigate('/login');
  };

  return (
    <div className="mesh-bg flex min-h-screen">
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-white/8 bg-[#0c0d12]/95 backdrop-blur-xl transition-transform lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-3 border-b border-white/8 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-[family-name:var(--font-display)] text-lg text-white">Aivura</p>
            <p className="text-xs text-zinc-500">Admin Portal</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? 'bg-violet-600/20 text-violet-200' : 'text-zinc-400 hover:bg-white/5'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/8 p-4">
          <a
            href="https://t.me/Aivura_bot"
            target="_blank"
            rel="noreferrer"
            className="mb-3 flex items-center gap-2 rounded-xl bg-violet-600/15 px-3 py-2 text-xs text-violet-200 hover:bg-violet-600/25"
          >
            <Bot className="h-3.5 w-3.5" /> @Aivura_bot
          </a>
          <p className="mb-2 text-xs text-zinc-500">Students use Telegram only</p>
          <button type="button" onClick={logout} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-zinc-400 hover:bg-white/5 hover:text-red-300">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>
      {open && <button type="button" className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setOpen(false)} />}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center border-b border-white/8 px-4 py-3 lg:px-8">
          <button type="button" className="lg:hidden p-2" onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></button>
          <p className="text-sm text-zinc-500">University & IT · Admin-managed users</p>
        </header>
        <main className="flex-1 p-4 lg:p-8"><Outlet /></main>
      </div>
    </div>
  );
}
