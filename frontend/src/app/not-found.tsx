'use client';

import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <div className="text-center">
        <h1 className="mb-2 text-4xl font-bold text-white">404</h1>
        <p className="mb-6 text-slate-400">找不到此頁面</p>
        <Link
          href="/"
          className="inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
        >
          返回首頁
        </Link>
      </div>
    </div>
  );
}
