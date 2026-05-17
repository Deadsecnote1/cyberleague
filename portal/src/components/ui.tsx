import type { ReactNode } from 'react';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`glass rounded-2xl p-5 transition hover:border-white/15 ${className}`}>
      {children}
    </div>
  );
}

export function Badge({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'success' | 'warn' | 'accent' }) {
  const tones = {
    default: 'bg-white/8 text-zinc-300',
    success: 'bg-emerald-500/15 text-emerald-300',
    warn: 'bg-amber-500/15 text-amber-300',
    accent: 'bg-violet-500/20 text-violet-200',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  className = '',
  disabled,
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'ghost' | 'outline';
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit';
}) {
  const variants = {
    primary: 'bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-900/40',
    ghost: 'bg-white/5 hover:bg-white/10 text-zinc-200',
    outline: 'border border-white/15 hover:bg-white/5 text-zinc-200',
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:opacity-50 ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function StatCard({ label, value, sub, icon }: { label: string; value: string | number; sub?: string; icon: ReactNode }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="rounded-xl bg-violet-500/15 p-2.5 text-violet-300">{icon}</div>
      </div>
      <div>
        <p className="text-2xl font-semibold tracking-tight text-white">{value}</p>
        <p className="text-sm text-zinc-400">{label}</p>
        {sub && <p className="mt-1 text-xs text-zinc-500">{sub}</p>}
      </div>
    </Card>
  );
}
