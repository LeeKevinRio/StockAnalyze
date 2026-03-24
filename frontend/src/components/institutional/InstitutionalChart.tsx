'use client';

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';

export interface InstitutionalDayData {
  date: string;
  foreign_net: number;
  trust_net: number;
  dealer_net: number;
  total_net: number;
}

interface InstitutionalChartProps {
  data: InstitutionalDayData[];
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

export function InstitutionalChart({ data }: InstitutionalChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg bg-slate-900 py-8 text-center text-slate-400">
        尚無法人買賣資料
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-slate-900 p-4">
      <h4 className="mb-3 text-sm font-medium text-slate-300">三大法人買賣超</h4>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateShort}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
          />
          <YAxis
            tickFormatter={formatNumber}
            tick={{ fill: '#64748b', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            width={60}
          />
          <Tooltip
            {...tooltipStyle}
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                foreign_net: '外資',
                trust_net: '投信',
                dealer_net: '自營商',
              };
              return [formatNumber(Number(value)), labels[String(name)] ?? String(name)];
            }}
            labelFormatter={(label) => formatDateShort(String(label))}
          />
          <Legend
            formatter={(value) => {
              const labels: Record<string, string> = {
                foreign_net: '外資',
                trust_net: '投信',
                dealer_net: '自營商',
              };
              return labels[value] ?? value;
            }}
            wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
          />
          <ReferenceLine y={0} stroke="#475569" />
          <Bar
            dataKey="foreign_net"
            stackId="a"
            fill="#3b82f6"
            name="foreign_net"
            isAnimationActive={false}
          />
          <Bar
            dataKey="trust_net"
            stackId="a"
            fill="#f97316"
            name="trust_net"
            isAnimationActive={false}
          />
          <Bar
            dataKey="dealer_net"
            stackId="a"
            fill="#a855f7"
            name="dealer_net"
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
