'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Sparkles, RefreshCw, ArrowRight, Info } from 'lucide-react';
import { useScreener } from '@/hooks/useAnalysis';
import { analysisAPI } from '@/lib/api';
import { scoreTextClass, scoreHex, changeTextClass, signalMeta } from '@/lib/marketColors';
import { Skeleton } from '@/components/ui/skeleton';
import type { ScreenerPick } from '@/lib/types';

const SIGNAL_FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'strong_buy', label: '強力買進' },
  { key: 'buy', label: '買進' },
  { key: 'neutral', label: '中性' },
  { key: 'sell', label: '賣出' },
  { key: 'strong_sell', label: '強力賣出' },
];

const SORTS = [
  { key: 'overall', label: '綜合評分' },
  { key: 'technical', label: '技術面' },
  { key: 'fundamental', label: '基本面' },
  { key: 'institutional', label: '籌碼面' },
  { key: 'confidence', label: '信心度' },
  { key: 'change', label: '今日漲幅' },
];

const DIMS: { key: keyof ScreenerPick['scores']; label: string }[] = [
  { key: 'news', label: '消息' },
  { key: 'fundamental', label: '基本' },
  { key: 'technical', label: '技術' },
  { key: 'institutional', label: '籌碼' },
  { key: 'macro', label: '總經' },
];

function DimBar({ score }: { score: number }) {
  // -100..100 → bar around a centre line
  const pct = Math.min(100, Math.abs(score));
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className="absolute top-0 h-full rounded-full"
        style={{
          width: `${pct / 2}%`,
          left: score >= 0 ? '50%' : `${50 - pct / 2}%`,
          backgroundColor: scoreHex(score),
        }}
      />
    </div>
  );
}

export default function ScreenerPage() {
  const [signal, setSignal] = useState('all');
  const [sort, setSort] = useState('overall');
  const [refreshing, setRefreshing] = useState(false);

  const params = { signal, sort, limit: 30 };
  const { data, isLoading, mutate } = useScreener(params);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const fresh = await analysisAPI.refreshScreener(params);
      mutate(fresh, { revalidate: false });
    } catch {
      // surface nothing fancy; SWR keeps last data
    } finally {
      setRefreshing(false);
    }
  }

  const picks = data ?? [];

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
              <Sparkles className="h-6 w-6 text-emerald-400" /> AI 選股
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              五維度綜合評分自動排名熱門權值股，紅多綠空，一眼看出強弱。
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? '掃描中…' : '重新掃描'}
          </button>
        </div>

        {/* Controls */}
        <div className="mb-5 space-y-3">
          <div className="flex flex-wrap gap-2">
            {SIGNAL_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setSignal(f.key)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  signal === f.key
                    ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">排序：</span>
            {SORTS.map((s) => (
              <button
                key={s.key}
                onClick={() => setSort(s.key)}
                className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
                  sort === s.key
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full bg-slate-800" />
            ))}
          </div>
        ) : picks.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-10 text-center">
            <Info className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            <p className="text-sm text-slate-400">
              尚無分析資料。點擊「重新掃描」讓 AI 計算熱門股的五維度評分（首次約需 30-60 秒）。
            </p>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? '掃描中…' : '開始掃描'}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {picks.map((p, i) => {
              const sig = signalMeta(p.overall_signal);
              const chg = p.change_percent ?? 0;
              return (
                <Link
                  key={p.stock_id}
                  href={`/stock/?id=${p.stock_id}`}
                  className="group flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900 p-3 transition-colors hover:border-emerald-500/40 hover:bg-slate-800/70 sm:p-4"
                >
                  {/* Rank */}
                  <div className="w-6 shrink-0 text-center text-sm font-bold text-slate-600">
                    {i + 1}
                  </div>

                  {/* Name + price */}
                  <div className="w-32 shrink-0">
                    <div className="flex items-baseline gap-1.5">
                      <span className="truncate font-medium text-white">{p.name}</span>
                      <span className="font-mono text-xs text-slate-500">{p.stock_id}</span>
                    </div>
                    <div className="mt-0.5 flex items-baseline gap-2">
                      <span className="text-sm text-slate-300">
                        {p.close != null ? Number(p.close).toFixed(2) : '—'}
                      </span>
                      {p.change_percent != null && (
                        <span className={`text-xs ${changeTextClass(chg)}`}>
                          {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Overall score */}
                  <div className="w-16 shrink-0 text-center">
                    <div className={`text-2xl font-bold ${scoreTextClass(p.overall_score)}`}>
                      {Math.round(p.overall_score)}
                    </div>
                    <div className="text-[10px] text-slate-500">綜合</div>
                  </div>

                  {/* Signal */}
                  <span className={`hidden shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium sm:inline-block ${sig.cls}`}>
                    {sig.label}
                  </span>

                  {/* Dimension bars */}
                  <div className="hidden flex-1 grid-cols-5 gap-3 md:grid">
                    {DIMS.map((d) => (
                      <div key={d.key}>
                        <div className="mb-1 flex items-center justify-between text-[10px] text-slate-500">
                          <span>{d.label}</span>
                          <span className={scoreTextClass(p.scores[d.key])}>
                            {Math.round(p.scores[d.key])}
                          </span>
                        </div>
                        <DimBar score={p.scores[d.key]} />
                      </div>
                    ))}
                  </div>

                  {/* Target price */}
                  <div className="hidden w-20 shrink-0 text-right lg:block">
                    {p.target_price != null ? (
                      <>
                        <div className="text-sm font-medium text-amber-400">
                          {Number(p.target_price).toFixed(1)}
                        </div>
                        <div className="text-[10px] text-slate-500">目標價</div>
                      </>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </div>

                  <ArrowRight className="h-4 w-4 shrink-0 text-slate-600 transition-colors group-hover:text-emerald-400" />
                </Link>
              );
            })}
          </div>
        )}

        <p className="mt-6 text-center text-xs text-slate-600">
          評分僅供參考，不構成投資建議。資料來源 FinMind、Yahoo Finance。
        </p>
      </div>
    </div>
  );
}
