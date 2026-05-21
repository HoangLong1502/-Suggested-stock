'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, Home, Layers } from 'lucide-react';

const linkBase =
  'inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition';

export default function AppNavbar() {
  const pathname = usePathname();
  const isHome = pathname === '/';
  const isSectors = pathname === '/sectors';

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#08101e]/90 backdrop-blur-xl">
      <nav className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-6">
        <Link
          href="/"
          className={`${linkBase} ${isHome ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`}
        >
          <Home className="h-4 w-4" />
          Dashboard
        </Link>

        <Link
          href="/sectors"
          className={`${linkBase} ring-1 ${
            isSectors
              ? 'bg-gradient-to-r from-violet-600/90 to-indigo-600/90 text-white ring-violet-400/40 shadow-lg shadow-violet-900/30'
              : 'border border-violet-500/30 bg-violet-950/50 text-violet-100 hover:bg-violet-900/60 hover:text-white ring-violet-500/20'
          }`}
        >
          <Layers className="h-4 w-4" />
          Phân tích ngành
        </Link>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <BarChart3 className="h-4 w-4 text-slate-400" />
          <span className="hidden sm:inline">VN market</span>
        </div>
      </nav>
    </header>
  );
}
