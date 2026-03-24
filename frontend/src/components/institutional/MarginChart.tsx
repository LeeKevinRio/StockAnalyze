'use client';

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export interface MarginDayData {
  date: string;
  margin_balance: number;
  short_balance: number;
  margin_change: number;
  utilization: number;
}

interface MarginChartProps {
  data: MarginDayData[];
}

function formatDateShort(dateStr: string) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`;
  return dateStr;
}

function formatNumber(value: number) {
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

export function MarginChart({ data }: MarginChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg bg-slate-900 py-8 text-center text-slate-400">
        尚無融資融券資料
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-slate-900 p-4">
      <h4 className="mb-3 text-sm font-medium text-slate-300">融資融券走勢</h4>
      <ResponsiveContainer width="100%" height={250}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateShort}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            yAxisId="left"
            tickFormatter={formatNumber}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            width={60}
            label={{
              value: '融資餘額',
              angle: -90,
              position: 'insideLeft',
              fill: '#64748b',
              fontSize: 10,
              offset: -5,
            }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickFormatter={formatNumber}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            width={60}
            label={{
              value: '融券餘額',
              angle: 90,
              position: 'insideRight',
              fill: '#64748b',
              fontSize: 10,
              offset: -5,
            }}
          />
          <Tooltip
            {...tooltipStyle}
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                margin_balance: '融資餘額',
                short_balance: '融券餘額',
              };
              return [formatNumber(Number(value)), labels[String(name)] ?? String(name)];
            }}
            labelFormatter={(label) => formatDateShort(String(label))}
          />
          <Legend
            formatter={(value) => {
              const labels: Record<string, string> = {
                margin_balance: '融資餘額',
                short_balance: '融券餘額',
              };
              return labels[value] ?? value;
            }}
            wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
          />
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="margin_balance"
            fill="rgba(59,130,246,0.2)"
            stroke="#3b82f6"
            strokeWidth={1.5}
            name="margin_balance"
            isAnimationActive={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="short_balance"
            stroke="#ef4444"
            strokeWidth={1.5}
            dot={false}
            name="short_balance"
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
