'use client';

import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { scoreTextClass } from '@/lib/marketColors';

interface DimensionScoreCardProps {
  name: string;
  score: number;   // -100 to 100
  signal: string;   // 'bullish' | 'bearish' | 'neutral'
  icon: ReactNode;
}

// Taiwan convention (紅漲綠跌): high score = red, low score = green.
const getScoreColor = scoreTextClass;

function getSignalBadge(signal: string) {
  switch (signal) {
    case 'bullish':
      return (
        <Badge variant="outline" className="border-red-500/30 bg-red-500/20 text-red-400">
          看多
        </Badge>
      );
    case 'bearish':
      return (
        <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/20 text-emerald-400">
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
      </CardContent>
    </Card>
  );
}
