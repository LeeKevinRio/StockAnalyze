'use client';

import { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { LineChart as LineChartIcon, Play } from 'lucide-react';
import { backtestAPI } from '@/lib/api';
import { useStockSearch } from '@/hooks/useStock';
import { changeTextClass } from '@/lib/marketColors';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import type { BacktestResult } from '@/lib/types';

const STRATEGIES = [
  { key: 'ma_cross' as const, label: '均線交叉', desc: '黃金交叉買進、死亡交叉賣出' },
  { key: 'rsi' as const, label: 'RSI 逆勢', desc: 'RSI 脫離超賣買進、跌落超買賣出' },
];

const RANGES = [
  { days: 120, label: '半年' },
  { days: 250, label: '一年' },
];

function formatDateShort(d: string) {
  const parts = d.split('-');
  return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : d;
}

function StatTile({ label, value, cls = 'text-white' }: { label: string; value: string; cls?: string }) {
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardContent className="p-4">
        <div className="text-xs text-slate-400">{label}</div>
        <div className={`mt-1 text-xl font-bold ${cls}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

export default function BacktestPage() {
  const [query, setQuery] = useState('');
  const [stockId, setStockId] = useState('');
  const [showList, setShowList] = useState(false);
  const [strategy, setStrategy] = useState<'ma_cross' | 'rsi'>('ma_cross');
  const [days, setDays] = useState(250);
  const [fast, setFast] = useState(5);
  const [slow, setSlow] = useState(20);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const { data: results } = useStockSearch(showList ? query.trim() : '');

  async function run() {
    if (!stockId) {
      setError('請先搜尋並選擇一檔股票');
      return;
    }
    setBusy(true);
    setError('');
    try {
      setResult(await backtestAPI.run(stockId, strategy, days, fast, slow));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : '回測失敗');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <LineChartIcon className="h-6 w-6 text-emerald-400" /> 策略回測
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            用歷史股價模擬簡單交易策略,與買入持有比較。收盤價成交、未含手續費,結果僅供參考。
          </p>
        </div>

        {/* Controls */}
        <div className="mb-6 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <div className="relative">
              <Input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setStockId('');
                  setShowList(true);
                }}
                placeholder="搜尋代號或名稱,例如 2330"
                className="border-slate-700 bg-slate-800 text-sm text-white placeholder:text-slate-500"
              />
              {showList && !stockId && results && results.length > 0 && (
                <ul className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 py-1 shadow-xl">
                  {results.map((r) => (
                    <li key={r.stock_id}>
                      <button
                        type="button"
                        onClick={() => {
                          setStockId(r.stock_id);
                          setQuery(`${r.stock_id} ${r.name}`);
                          setShowList(false);
                        }}
                        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-700"
                      >
                        <span className="font-mono text-emerald-400">{r.stock_id}</span>
                        <span className="text-white">{r.name}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={run}
              disabled={busy}
              className="flex items-center justify-center gap-2 rounded-lg bg-emerald-500/20 px-6 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/30 disabled:opacity-60"
            >
              <Play className="h-4 w-4" /> {busy ? '回測中…' : '執行回測'}
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-4">
            <div className="flex gap-1.5">
              {STRATEGIES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStrategy(s.key)}
                  title={s.desc}
                  className={`rounded-md px-3 py-1 text-xs transition-colors ${
                    strategy === s.key
                      ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="flex gap-1.5">
              {RANGES.map((r) => (
                <button
                  key={r.days}
                  onClick={() => setDays(r.days)}
                  className={`rounded-md px-3 py-1 text-xs transition-colors ${
                    days === r.days
                      ? 'bg-slate-700 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            {strategy === 'ma_cross' && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span>快線</span>
                <select
                  value={fast}
                  onChange={(e) => setFast(Number(e.target.value))}
                  className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-white"
                >
                  {[3, 5, 10].map((v) => <option key={v} value={v}>MA{v}</option>)}
                </select>
                <span>慢線</span>
                <select
                  value={slow}
                  onChange={(e) => setSlow(Number(e.target.value))}
                  className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-white"
                >
                  {[20, 60].map((v) => <option key={v} value={v}>MA{v}</option>)}
                </select>
              </div>
            )}
          </div>
          {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatTile
                label="策略報酬"
                value={`${result.strategy_return_pct >= 0 ? '+' : ''}${result.strategy_return_pct}%`}
                cls={changeTextClass(result.strategy_return_pct)}
              />
              <StatTile
                label="買入持有"
                value={`${result.buy_hold_return_pct >= 0 ? '+' : ''}${result.buy_hold_return_pct}%`}
                cls={changeTextClass(result.buy_hold_return_pct)}
              />
              <StatTile
                label="交易次數 / 勝率"
                value={`${result.trade_count} 次${result.win_rate != null ? ` / ${result.win_rate}%` : ''}`}
              />
              <StatTile label="最大回撤" value={`-${result.max_drawdown_pct}%`} cls="text-emerald-400" />
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-3 text-sm font-medium text-slate-300">
                {result.name}({result.stock_id})淨值曲線 — {result.start_date} ~ {result.end_date},期初 = 100
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={result.curve} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDateShort}
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={{ stroke: '#334155' }}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={{ stroke: '#334155' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      fontSize: 12,
                    }}
                    labelStyle={{ color: '#94a3b8' }}
                    formatter={(value, name) => [
                      Number(value).toFixed(1),
                      name === 'strategy' ? '策略' : '買入持有',
                    ]}
                  />
                  <Legend
                    formatter={(v) => (v === 'strategy' ? '策略' : '買入持有')}
                    wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
                  />
                  <ReferenceLine y={100} stroke="#475569" />
                  <Line
                    type="monotone"
                    dataKey="strategy"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="buy_hold"
                    stroke="#94a3b8"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {result.trades.length > 0 && (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                      <th className="px-4 py-2.5 font-normal">日期</th>
                      <th className="px-4 py-2.5 font-normal">動作</th>
                      <th className="px-4 py-2.5 text-right font-normal">價格</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} className="border-b border-slate-800/60 last:border-0">
                        <td className="px-4 py-2 text-slate-300">{t.date}</td>
                        <td className={`px-4 py-2 ${t.action === 'buy' ? 'text-red-400' : 'text-emerald-400'}`}>
                          {t.action === 'buy' ? '買進' : '賣出'}
                        </td>
                        <td className="px-4 py-2 text-right text-slate-300">{t.price}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {result.in_position && (
                  <p className="px-4 py-2 text-xs text-slate-500">※ 期末仍持有部位,以最後收盤價計值。</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
