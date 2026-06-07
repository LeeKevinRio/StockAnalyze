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

/**
 * The backend returns each indicator as parallel numeric arrays (no dates),
 * and the arrays have different lengths (e.g. MACD signal is shorter than the
 * MACD line). We align every series to the most recent `dates` by taking the
 * trailing slice, which keeps the right edge (latest values) correct.
 */
interface IndicatorPanelProps {
  indicators: {
    macd?: { macd: number[]; signal: number[]; histogram: number[] };
    rsi?: number[];
    kd?: { k: number[]; d: number[] };
  };
  /** Ascending price dates used to label the indicator x-axis. */
  dates?: string[];
}

function formatDateShort(dateStr: string) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`;
  return dateStr;
}

function tail<T>(arr: T[] | undefined, n: number): T[] {
  if (!arr || arr.length === 0) return [];
  return arr.slice(arr.length - n);
}

function labelsFor(len: number, dates?: string[]): string[] {
  if (dates && dates.length >= len) return dates.slice(dates.length - len);
  return Array.from({ length: len }, (_, i) => String(i + 1));
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

export function IndicatorPanel({ indicators, dates }: IndicatorPanelProps) {
  // MACD — align macd/signal/histogram to their common (shortest) length.
  const macdRaw = indicators?.macd;
  let macdData: { date: string; macd: number; signal: number; histogram: number }[] = [];
  if (macdRaw?.signal?.length && macdRaw?.macd?.length) {
    const L = Math.min(macdRaw.macd.length, macdRaw.signal.length, macdRaw.histogram.length);
    const macdT = tail(macdRaw.macd, L);
    const sigT = tail(macdRaw.signal, L);
    const histT = tail(macdRaw.histogram, L);
    const lbls = labelsFor(L, dates);
    macdData = macdT.map((v, i) => ({ date: lbls[i], macd: v, signal: sigT[i], histogram: histT[i] }));
  }

  // RSI — flat array.
  const rsiRaw = indicators?.rsi ?? [];
  const rsiData = rsiRaw.length
    ? labelsFor(rsiRaw.length, dates).map((d, i) => ({ date: d, rsi: rsiRaw[i] }))
    : [];

  // KD — k/d parallel arrays.
  const kdRaw = indicators?.kd;
  let kdData: { date: string; k: number; d: number }[] = [];
  if (kdRaw?.k?.length && kdRaw?.d?.length) {
    const L = Math.min(kdRaw.k.length, kdRaw.d.length);
    const kT = tail(kdRaw.k, L);
    const dT = tail(kdRaw.d, L);
    const lbls = labelsFor(L, dates);
    kdData = kT.map((v, i) => ({ date: lbls[i], k: v, d: dT[i] }));
  }

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
                    fill={entry.histogram >= 0 ? '#ef4444' : '#22c55e'}
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
