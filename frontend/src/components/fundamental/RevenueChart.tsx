'use client';

import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

interface RevenueChartProps {
  statements: {
    report_year: number;
    report_quarter: number;
    revenue: number;
  }[];
}

function formatLargeNumber(value: number) {
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(1)}億`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(0)}萬`;
  return value.toLocaleString();
}

const tooltipStyle = {
  contentStyle: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: 12,
  },
  labelStyle: { color: '#94a3b8' },
};

export function RevenueChart({ statements }: RevenueChartProps) {
  if (!statements || statements.length === 0) {
    return (
      <div className="rounded-lg bg-slate-900 py-8 text-center text-slate-400">
        尚無營收資料
      </div>
    );
  }

  // Sort by year and quarter
  const sorted = [...statements].sort(
    (a, b) => a.report_year * 10 + a.report_quarter - (b.report_year * 10 + b.report_quarter)
  );

  // Build chart data with YoY growth
  const chartData = sorted.map((s, idx) => {
    const label = `${s.report_year}Q${s.report_quarter}`;
    // Find same quarter previous year
    const prevYear = sorted.find(
      (p) => p.report_year === s.report_year - 1 && p.report_quarter === s.report_quarter
    );
    const yoyGrowth =
      prevYear && prevYear.revenue > 0
        ? ((s.revenue - prevYear.revenue) / prevYear.revenue) * 100
        : null;

    return {
      quarter: label,
      revenue: s.revenue,
      yoy_growth: yoyGrowth,
    };
  });

  return (
    <div className="rounded-lg bg-slate-900 p-4">
      <h4 className="mb-3 text-sm font-medium text-slate-300">季營收趨勢</h4>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="quarter"
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            yAxisId="left"
            tickFormatter={formatLargeNumber}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            width={60}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            width={50}
            tickFormatter={(v) => `${Number(v).toFixed(0)}%`}
          />
          <Tooltip
            {...tooltipStyle}
            formatter={(value, name) => {
              const v = Number(value);
              if (name === 'revenue') return [formatLargeNumber(v), '營收'];
              if (name === 'yoy_growth') return [`${v.toFixed(1)}%`, 'YoY 成長率'];
              return [String(value), String(name)];
            }}
          />
          <Legend
            formatter={(value) => {
              if (value === 'revenue') return '營收';
              if (value === 'yoy_growth') return 'YoY 成長率';
              return value;
            }}
            wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
          />
          <Bar
            yAxisId="left"
            dataKey="revenue"
            fill="#3b82f6"
            name="revenue"
            isAnimationActive={false}
            radius={[4, 4, 0, 0]}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="yoy_growth"
            stroke="#f97316"
            strokeWidth={2}
            dot={{ fill: '#f97316', r: 3 }}
            name="yoy_growth"
            isAnimationActive={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
