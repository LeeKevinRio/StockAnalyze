'use client';

import { UP_HEX, DOWN_HEX } from '@/lib/marketColors';

interface SparklineProps {
  values: number[];
  /** true = up (red), false = down (green) — Taiwan convention. */
  up: boolean;
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkline({ values, up, width = 120, height = 36, className }: SparklineProps) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / span) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const stroke = up ? UP_HEX : DOWN_HEX;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className={className ?? 'h-9 w-full'}>
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}
