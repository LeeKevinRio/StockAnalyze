'use client';

import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ComposedChart,
} from 'recharts';

interface IndicatorPanelProps {
  indicators: {
    macd?: { date: string; macd: number; signal: number; histogram: number }[];
    rsi?: { date: string; rsi: number }[];
    kd?: { date: string; k: number; d: number }[];
  };
}

function formatDateShort(dateStr: string) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`;
  return dateStr;
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

export function IndicatorPanel({ indicators }: IndicatorPanelProps) {
  const macdData = indicators?.macd ?? [];
  const rsiData = indicators?.rsi ?? [];
  const kdData = indicators?.kd ?? [];

  if (macdData.length === 0 && rsiData.length === 0 && kdData.length === 0) {
    return (
      <div className="rounded-lg bg-slate-900 py-8 text-center text-slate-400">
        尚無技術指標資料
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* MACD */}
      {macdData.length > 0 && (
        <div className="rounded-lg bg-slate-900 p-4">
          <h4 className="mb-2 text-sm font-medium text-slate-300">MACD</h4>
          <ResponsiveContainer width="100%" height={140}>
            <ComposedChart data={macdData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
                width={50}
              />
              <Tooltip
                {...tooltipStyle}
                formatter={(value, name) => [
                  Number(value).toFixed(2),
                  name === 'macd' ? 'MACD' : name === 'signal' ? 'Signal' : 'Histogram',
                ]}
                labelFormatter={(label) => formatDateShort(String(label))}
              />
              <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
              <Bar
                dataKey="histogram"
                fill="#22c55e"
                name="histogram"
                isAnimationActive={false}
              >
                {macdData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.histogram >= 0 ? '#22c55e' : '#ef4444'}
                  />
                ))}
              </Bar>
              <Line
                type="monotone"
                dataKey="macd"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
                name="macd"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="signal"
                stroke="#f97316"
                strokeWidth={1.5}
                dot={false}
                name="signal"
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* RSI */}
      {rsiData.length > 0 && (
        <div className="rounded-lg bg-slate-900 p-4">
          <h4 className="mb-2 text-sm font-medium text-slate-300">RSI</h4>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={rsiData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
                width={35}
              />
              <Tooltip
                {...tooltipStyle}
                formatter={(value) => [Number(value).toFixed(2), 'RSI']}
                labelFormatter={(label) => formatDateShort(String(label))}
              />
              <ReferenceLine
                y={70}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: '70', fill: '#ef4444', fontSize: 10, position: 'right' }}
              />
              <ReferenceLine
                y={30}
                stroke="#22c55e"
                strokeDasharray="5 5"
                label={{ value: '30', fill: '#22c55e', fontSize: 10, position: 'right' }}
              />
              <Line
                type="monotone"
                dataKey="rsi"
                stroke="#a855f7"
                strokeWidth={1.5}
                dot={false}
                name="RSI"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* KD */}
      {kdData.length > 0 && (
        <div className="rounded-lg bg-slate-900 p-4">
          <h4 className="mb-2 text-sm font-medium text-slate-300">KD 指標</h4>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={kdData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={{ stroke: '#334155' }}
                width={35}
              />
              <Tooltip
                {...tooltipStyle}
                formatter={(value, name) => [
                  Number(value).toFixed(2),
                  name === 'k' ? 'K' : 'D',
                ]}
                labelFormatter={(label) => formatDateShort(String(label))}
              />
              <ReferenceLine
                y={80}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: '80', fill: '#ef4444', fontSize: 10, position: 'right' }}
              />
              <ReferenceLine
                y={20}
                stroke="#22c55e"
                strokeDasharray="5 5"
                label={{ value: '20', fill: '#22c55e', fontSize: 10, position: 'right' }}
              />
              <Line
                type="monotone"
                dataKey="k"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
                name="k"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="d"
                stroke="#f97316"
                strokeWidth={1.5}
                dot={false}
                name="d"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
