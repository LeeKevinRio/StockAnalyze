'use client';

import {
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import type { DimensionScore } from '@/lib/types';

interface RadarChartProps {
  dimensions: DimensionScore[];
}

// Map internal dimension names to display labels
const DIMENSION_LABELS: Record<string, string> = {
  news: '消息面',
  fundamental: '基本面',
  technical: '技術面',
  institutional: '籌碼面',
  macro: '總經面',
  // Fallback: use the name as-is if not in the map
};

export function RadarChart({ dimensions }: RadarChartProps) {
  // Normalize scores from [-100, 100] to [0, 100] for display
  const data = dimensions.map((d) => ({
    dimension: DIMENSION_LABELS[d.name] || d.name,
    score: (d.score + 100) / 2,
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RechartsRadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <Radar
          name="分析分數"
          dataKey="score"
          stroke="#38bdf8"
          fill="#38bdf8"
          fillOpacity={0.25}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
