'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { FileText, ChevronDown, ChevronUp, ArrowRight, Sparkles } from 'lucide-react';
import { useRecentReports, useScoreHistory } from '@/hooks/useAnalysis';
import { scoreTextClass, signalMeta } from '@/lib/marketColors';
import { Skeleton } from '@/components/ui/skeleton';

function formatDateShort(d: string | null) {
  if (!d) return '';
  const parts = d.split('-');
  return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : d;
}

function TrendChart({ stockId }: { stockId: string }) {
  const { data, isLoading } = useScoreHistory(stockId, 90);

  if (isLoading) return <Skeleton className="h-48 w-full bg-slate-800" />;
  if (!data || data.length < 2) {
    return (
      <p className="py-6 text-center text-xs text-slate-500">
        歷史資料不足(需至少兩天的報告),之後每日排程會自動累積。
      </p>
    );
  }

  return (
    <div>
      <h4 className="mb-2 text-xs text-slate-400">綜合評分走勢(近 {data.length} 份報告)</h4>
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="report_date"
            tickFormatter={formatDateShort}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            domain={[-100, 100]}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: 12,
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value) => [Number(value).toFixed(0), '綜合評分']}
            labelFormatter={(label) => String(label)}
          />
          <ReferenceLine y={0} stroke="#475569" />
          <Line
            type="monotone"
            dataKey="overall_score"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 2.5, fill: '#3b82f6' }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ReportsPage() {
  const { data, isLoading } = useRecentReports(50);
  const [expanded, setExpanded] = useState<string | null>(null);

  const reports = data ?? [];

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <FileText className="h-6 w-6 text-emerald-400" /> 報告中心
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            每日自動分析的最新報告與評分走勢。評分明顯下滑的持股值得留意。
          </p>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full bg-slate-800" />
            ))}
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-10 text-center text-sm text-slate-400">
            尚無分析報告。到「AI 選股」點「重新掃描」,或等每日 14:40 排程自動產生。
          </div>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => {
              const sig = signalMeta(r.overall_signal);
              const isOpen = expanded === r.stock_id;
              return (
                <div
                  key={r.stock_id}
                  className="rounded-xl border border-slate-800 bg-slate-900 transition-colors hover:border-slate-700"
                >
                  <button
                    onClick={() => setExpanded(isOpen ? null : r.stock_id)}
                    className="flex w-full items-center gap-3 p-3 text-left sm:p-4"
                  >
                    <div className="w-28 shrink-0">
                      <div className="flex items-baseline gap-1.5">
                        <span className="truncate text-sm font-medium text-white">{r.name}</span>
                        <span className="font-mono text-xs text-slate-500">{r.stock_id}</span>
                      </div>
                      <div className="mt-0.5 text-[10px] text-slate-500">{r.report_date}</div>
                    </div>

                    <div className={`w-12 shrink-0 text-center text-xl font-bold ${scoreTextClass(r.overall_score)}`}>
                      {Math.round(r.overall_score)}
                    </div>

                    <span className={`shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium ${sig.cls}`}>
                      {sig.label}
                    </span>

                    {r.has_full_report && (
                      <span className="hidden shrink-0 items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 sm:flex">
                        <Sparkles className="h-3 w-3" /> AI 完整報告
                      </span>
                    )}

                    <p className="hidden min-w-0 flex-1 truncate text-xs text-slate-400 md:block">
                      {r.short_term_outlook || '—'}
                    </p>

                    <span className="ml-auto shrink-0 text-slate-500">
                      {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </span>
                  </button>

                  {isOpen && (
                    <div className="border-t border-slate-800 p-4">
                      <TrendChart stockId={r.stock_id} />
                      {r.short_term_outlook && (
                        <p className="mt-3 text-xs leading-relaxed text-slate-300 md:hidden">
                          {r.short_term_outlook}
                        </p>
                      )}
                      <div className="mt-3 flex items-center justify-between">
                        <div className="flex gap-3 text-xs text-slate-400">
                          {r.target_price != null && (
                            <span>目標價 <span className="text-amber-400">{r.target_price}</span></span>
                          )}
                          {r.risk_level && <span>風險 {r.risk_level}</span>}
                          <span>信心 {(r.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <Link
                          href={`/stock/?id=${r.stock_id}`}
                          className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300"
                        >
                          查看完整報告 <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
