'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChipSummaryProps {
  analysis: {
    foreign_trend?: string;
    trust_trend?: string;
    dealer_trend?: string;
    consecutive_buy_days?: number;
    consecutive_sell_days?: number;
    score?: number;
    signal?: string;
    summary?: string;
  };
}

function getTrendIcon(trend: string | undefined) {
  if (!trend) return { icon: '—', color: 'text-slate-400' };
  if (trend === 'buying' || trend === 'bullish') return { icon: '▲', color: 'text-red-400' };
  if (trend === 'selling' || trend === 'bearish') return { icon: '▼', color: 'text-emerald-400' };
  return { icon: '●', color: 'text-yellow-400' };
}

function getTrendLabel(trend: string | undefined) {
  if (!trend) return '—';
  switch (trend) {
    case 'buying':
    case 'bullish':
      return '買超';
    case 'selling':
    case 'bearish':
      return '賣超';
    case 'neutral':
      return '中性';
    default:
      return trend;
  }
}

function getSignalBadge(signal: string | undefined) {
  if (!signal) return { label: '—', cls: 'bg-slate-700 text-slate-400' };
  switch (signal) {
    case 'bullish':
      return { label: '看多', cls: 'bg-red-500/20 text-red-400' };
    case 'bearish':
      return { label: '看空', cls: 'bg-emerald-500/20 text-emerald-400' };
    default:
      return { label: '中性', cls: 'bg-yellow-500/20 text-yellow-400' };
  }
}

function getScoreBg(score: number | undefined) {
  if (score == null) return 'bg-slate-700 text-slate-400';
  if (score >= 70) return 'bg-red-500/20 text-red-400';
  if (score >= 40) return 'bg-yellow-500/20 text-yellow-400';
  return 'bg-emerald-500/20 text-emerald-400';
}

export function ChipSummary({ analysis }: ChipSummaryProps) {
  const signalBadge = getSignalBadge(analysis?.signal);

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-white">籌碼分析摘要</CardTitle>
          <div className="flex items-center gap-2">
            {analysis?.score != null && (
              <span className={`rounded-lg px-3 py-1 text-lg font-bold ${getScoreBg(analysis.score)}`}>
                {analysis.score}
              </span>
            )}
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${signalBadge.cls}`}>
              {signalBadge.label}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Institutional trends grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* Foreign */}
          <div className="rounded-lg bg-slate-800/50 p-3">
            <div className="text-xs text-slate-400">外資動向</div>
            <div className="mt-1 flex items-center gap-1">
              <span className={`text-base font-bold ${getTrendIcon(analysis?.foreign_trend).color}`}>
                {getTrendIcon(analysis?.foreign_trend).icon}
              </span>
              <span className="text-sm font-medium text-white">
                {getTrendLabel(analysis?.foreign_trend)}
              </span>
            </div>
          </div>

          {/* Trust */}
          <div className="rounded-lg bg-slate-800/50 p-3">
            <div className="text-xs text-slate-400">投信動向</div>
            <div className="mt-1 flex items-center gap-1">
              <span className={`text-base font-bold ${getTrendIcon(analysis?.trust_trend).color}`}>
                {getTrendIcon(analysis?.trust_trend).icon}
              </span>
              <span className="text-sm font-medium text-white">
                {getTrendLabel(analysis?.trust_trend)}
              </span>
            </div>
          </div>

          {/* Consecutive buying days */}
          <div className="rounded-lg bg-slate-800/50 p-3">
            <div className="text-xs text-slate-400">連續買超</div>
            <div className="mt-1 text-lg font-bold text-red-400">
              {analysis?.consecutive_buy_days ?? 0}
              <span className="ml-0.5 text-xs font-normal text-slate-400">天</span>
            </div>
          </div>

          {/* Consecutive selling days */}
          <div className="rounded-lg bg-slate-800/50 p-3">
            <div className="text-xs text-slate-400">連續賣超</div>
            <div className="mt-1 text-lg font-bold text-emerald-400">
              {analysis?.consecutive_sell_days ?? 0}
              <span className="ml-0.5 text-xs font-normal text-slate-400">天</span>
            </div>
          </div>
        </div>

        {/* Summary text */}
        {analysis?.summary && (
          <p className="text-sm leading-relaxed text-slate-300">{analysis.summary}</p>
        )}
      </CardContent>
    </Card>
  );
}
