'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export interface TechnicalSignal {
  signal_type: string;
  direction: string;
  description: string;
  strength: string;
}

interface TechnicalSummaryProps {
  signals: TechnicalSignal[];
  score: number;
  summary: string;
}

function getScoreColor(score: number) {
  if (score >= 70) return 'text-emerald-400';
  if (score >= 40) return 'text-yellow-400';
  return 'text-red-400';
}

function getScoreBg(score: number) {
  if (score >= 70) return 'bg-emerald-500/20 text-emerald-400';
  if (score >= 40) return 'bg-yellow-500/20 text-yellow-400';
  return 'bg-red-500/20 text-red-400';
}

function getStrengthBadgeClass(strength: string) {
  switch (strength) {
    case 'strong':
      return 'bg-emerald-500/20 text-emerald-300';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-300';
    case 'weak':
      return 'bg-slate-500/20 text-slate-400';
    default:
      return 'bg-slate-500/20 text-slate-400';
  }
}

function getStrengthLabel(strength: string) {
  switch (strength) {
    case 'strong':
      return '強';
    case 'medium':
      return '中';
    case 'weak':
      return '弱';
    default:
      return strength;
  }
}

export function TechnicalSummary({ signals, score, summary }: TechnicalSummaryProps) {
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-white">技術分析摘要</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">技術分數</span>
            <span
              className={`rounded-lg px-3 py-1 text-lg font-bold ${getScoreBg(score)}`}
            >
              {score}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary paragraph */}
        {summary && (
          <p className="text-sm leading-relaxed text-slate-300">{summary}</p>
        )}

        {/* Signals list */}
        {signals.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-slate-400">偵測到的訊號</h4>
            <div className="space-y-2">
              {signals.map((signal, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 rounded-lg bg-slate-800/50 px-3 py-2"
                >
                  {/* Direction icon */}
                  <span
                    className={`text-lg font-bold ${
                      signal.direction === 'bullish'
                        ? 'text-emerald-400'
                        : signal.direction === 'bearish'
                          ? 'text-red-400'
                          : 'text-slate-400'
                    }`}
                  >
                    {signal.direction === 'bullish'
                      ? '▲'
                      : signal.direction === 'bearish'
                        ? '▼'
                        : '●'}
                  </span>

                  {/* Description */}
                  <span className="flex-1 text-sm text-slate-200">
                    {signal.description}
                  </span>

                  {/* Strength badge */}
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getStrengthBadgeClass(signal.strength)}`}
                  >
                    {getStrengthLabel(signal.strength)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">目前沒有偵測到明顯訊號</p>
        )}
      </CardContent>
    </Card>
  );
}
