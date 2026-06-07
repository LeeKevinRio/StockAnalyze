'use client';

import { Badge } from '@/components/ui/badge';

interface SentimentBadgeProps {
  sentiment: string | null;
  score: number | string | null;
}

export function SentimentBadge({ sentiment, score }: SentimentBadgeProps) {
  // score may arrive as a string (Decimal serialised by the backend).
  const numScore = score == null ? null : Number(score);
  const isPositive = (numScore !== null && numScore > 0.3) || sentiment === 'positive';
  const isNegative = (numScore !== null && numScore < -0.3) || sentiment === 'negative';

  let label: string;
  // Taiwan convention: 利多 (positive) = red, 利空 (negative) = green.
  let colorClasses: string;

  if (isPositive) {
    label = '利多';
    colorClasses = 'bg-red-500/20 text-red-400 border-red-500/30';
  } else if (isNegative) {
    label = '利空';
    colorClasses = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
  } else {
    label = '中性';
    colorClasses = 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  }

  return (
    <Badge variant="outline" className={colorClasses}>
      {label}
      {numScore !== null && !Number.isNaN(numScore) && (
        <span className="ml-1 text-[10px] opacity-80">
          {numScore > 0 ? '+' : ''}
          {numScore.toFixed(2)}
        </span>
      )}
    </Badge>
  );
}
