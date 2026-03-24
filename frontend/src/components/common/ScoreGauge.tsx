'use client';

import { useEffect, useState } from 'react';

interface ScoreGaugeProps {
  score: number; // -100 to 100
  label: string;
  size?: 'sm' | 'md' | 'lg';
}

function getScoreColor(score: number): string {
  if (score >= 60) return '#22c55e';   // green - strong buy
  if (score >= 20) return '#86efac';   // light green - buy
  if (score >= -20) return '#94a3b8';  // gray - neutral
  if (score >= -60) return '#f97316';  // orange - sell
  return '#ef4444';                     // red - strong sell
}

const SIZES = {
  sm: { outer: 80, stroke: 6, fontSize: 'text-lg', labelSize: 'text-[10px]' },
  md: { outer: 120, stroke: 8, fontSize: 'text-2xl', labelSize: 'text-xs' },
  lg: { outer: 160, stroke: 10, fontSize: 'text-3xl', labelSize: 'text-sm' },
} as const;

export function ScoreGauge({ score, label, size = 'md' }: ScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    // Trigger animation after mount
    const frame = requestAnimationFrame(() => {
      setAnimatedScore(score);
    });
    return () => cancelAnimationFrame(frame);
  }, [score]);

  const { outer, stroke, fontSize, labelSize } = SIZES[size];
  const radius = (outer - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  // Normalize score from [-100, 100] to [0, 1]
  const normalized = (animatedScore + 100) / 200;
  const dashOffset = circumference * (1 - normalized);
  const color = getScoreColor(score);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={outer} height={outer} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={outer / 2}
          cy={outer / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-slate-700"
        />
        {/* Colored arc */}
        <circle
          cx={outer / 2}
          cy={outer / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
        />
      </svg>
      {/* Score number in center - overlay on top of SVG */}
      <div
        className="flex items-center justify-center"
        style={{ marginTop: -outer + (outer - stroke) / 2, height: outer }}
      >
        <span className={`${fontSize} font-bold`} style={{ color }}>
          {score > 0 ? '+' : ''}{score}
        </span>
      </div>
      {/* Label below */}
      <span className={`${labelSize} text-muted-foreground`}>{label}</span>
    </div>
  );
}
