'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  TrendingUp,
  Home,
  Star,
  PieChart,
  LineChart,
  Sparkles,
  Briefcase,
  FileText,
  Bell,
  Settings,
  Moon,
} from 'lucide-react';
import { SearchBar } from './SearchBar';
import { MarketIndexWidget } from './MarketIndexWidget';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  ready: boolean; // false = 敬請期待 placeholder
}

const NAV: NavItem[] = [
  { label: '首頁', href: '/', icon: Home, ready: true },
  { label: '市場新聞', href: '/news', icon: PieChart, ready: true },
  { label: '自選股', href: '#', icon: Star, ready: false },
  { label: '市場總覽', href: '#', icon: LineChart, ready: false },
  { label: '策略回測', href: '#', icon: LineChart, ready: false },
  { label: 'AI 選股', href: '#', icon: Sparkles, ready: false },
  { label: '投資組合', href: '#', icon: Briefcase, ready: false },
  { label: '報告中心', href: '#', icon: FileText, ready: false },
  { label: '通知中心', href: '#', icon: Bell, ready: false },
  { label: '設定', href: '#', icon: Settings, ready: false },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-slate-800 bg-slate-900">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15">
          <TrendingUp className="h-5 w-5 text-emerald-400" />
        </div>
        <div className="leading-tight">
          <div className="text-base font-bold text-white">股市智析</div>
          <div className="text-[10px] text-slate-400">AI 投資決策平台</div>
        </div>
      </Link>

      {/* Search */}
      <div className="px-3 pb-2">
        <SearchBar />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            const active = item.ready && (item.href === '/' ? pathname === '/' : pathname.startsWith(item.href));
            const Icon = item.icon;
            const base = 'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors';
            if (!item.ready) {
              return (
                <li key={item.label}>
                  <span
                    title="敬請期待"
                    className={`${base} cursor-not-allowed text-slate-500`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                    <span className="ml-auto rounded bg-slate-800 px-1.5 py-0.5 text-[9px] text-slate-500">即將推出</span>
                  </span>
                </li>
              );
            }
            return (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className={`${base} ${active ? 'bg-emerald-500/15 font-medium text-emerald-300' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Market index widget */}
      <div className="px-3 pb-2">
        <MarketIndexWidget />
      </div>

      {/* Dark mode indicator (app is dark-only for now) */}
      <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3">
        <span className="flex items-center gap-2 text-xs text-slate-400">
          <Moon className="h-4 w-4" /> 深色模式
        </span>
        <span className="flex h-5 w-9 items-center rounded-full bg-emerald-500/80 px-0.5">
          <span className="ml-auto h-4 w-4 rounded-full bg-white" />
        </span>
      </div>
    </aside>
  );
}
