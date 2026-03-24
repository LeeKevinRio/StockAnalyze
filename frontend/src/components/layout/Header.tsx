'use client';

import Link from 'next/link';
import { TrendingUp, ExternalLink } from 'lucide-react';
import { SearchBar } from './SearchBar';

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800 bg-slate-900 text-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        {/* Logo / Brand */}
        <Link href="/" className="flex shrink-0 items-center gap-2 font-bold">
          <TrendingUp className="h-5 w-5 text-emerald-400" />
          <span className="hidden text-lg sm:inline">台股分析</span>
        </Link>

        {/* Search Bar - grows to fill center */}
        <div className="min-w-0 flex-1">
          <SearchBar />
        </div>

        {/* Navigation Links */}
        <nav className="hidden items-center gap-1 sm:flex">
          <Link
            href="/"
            className="rounded-md px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
          >
            首頁
          </Link>
          <Link
            href="/news"
            className="rounded-md px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
          >
            新聞
          </Link>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-1 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
          >
            <ExternalLink className="h-5 w-5" />
          </a>
        </nav>
      </div>
    </header>
  );
}
