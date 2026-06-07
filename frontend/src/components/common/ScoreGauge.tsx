'use client';

import { useEffect, useState } from 'react';
import { scoreHex } from '@/lib/marketColors';

interface ScoreGaugeProps {
  score: number; // -100 to 100
  label: string;
  size?: 'sm' | 'md' | 'lg';
}

// Taiwan convention (紅漲綠跌): high score = red, low score = green.
const getScoreColor = scoreHex;

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
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: outer, height: outer }}>
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
        {/* Score number centered over the ring */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`${fontSize} font-bold`} style={{ color }}>
            {score > 0 ? '+' : ''}{score}
          </span>
        </div>
      </div>
      {/* Label below */}
      <span className={`${labelSize} text-muted-foreground`}>{label}</span>
    </div>
  );
}
