'use client';

import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface DimensionScoreCardProps {
  name: string;
  score: number;   // -100 to 100
  signal: string;   // 'bullish' | 'bearish' | 'neutral'
  icon: ReactNode;
}

function getScoreColor(score: number): string {
  if (score >= 60) return 'text-emerald-400';
  if (score >= 20) return 'text-emerald-300';
  if (score >= -20) return 'text-slate-400';
  if (score >= -60) return 'text-orange-400';
  return 'text-red-400';
}

function getSignalBadge(signal: string) {
  switch (signal) {
    case 'bullish':
      return (
        <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/20 text-emerald-400">
          看多
        </Badge>
      );
    case 'bearish':
      return (
        <Badge variant="outline" className="border-red-500/30 bg-red-500/20 text-red-400">
          看空
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="border-slate-500/30 bg-slate-500/20 text-slate-400">
          中性
        </Badge>
      );
  }
}

export function DimensionScoreCard({ name, score, signal, icon }: DimensionScoreCardProps) {
  // Normalize score from [-100, 100] to [0, 100] for progress bar
  const progressPercent = ((score + 100) / 200) * 100;

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-4">
        {/* Icon + name */}
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-sm font-medium">{name}</span>
        </div>

        {/* Large score */}
        <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
          {score > 0 ? '+' : ''}{score}
        </span>

        {/* Signal badge */}
        {getSignalBadge(signal)}

        {/* Progress bar: -100 to 100 */}
        <div className="w-full">
          <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-slate-700">
            <div
              className="absolute left-0 top-0 h-full rounded-full bg-current transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
            {/* Center tick mark for 0 */}
            <div className="absolute left-1/2 top-0 h-full w-px bg-slate-500" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
