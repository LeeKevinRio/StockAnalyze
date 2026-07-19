'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { Briefcase, Plus, Trash2, Pencil, LogIn } from 'lucide-react';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useStockSearch } from '@/hooks/useStock';
import { changeTextClass } from '@/lib/marketColors';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import type { PortfolioHolding } from '@/lib/types';

// Categorical palette — fixed order, validated for dark surface + CVD
// (dataviz six checks). Directional red/green stay reserved for P/L.
const PIE_COLORS = ['#3b82f6', '#ea580c', '#a855f7', '#0891b2', '#ec4899', '#a16207'];
const OTHER_COLOR = '#64748b';

function fmtMoney(v: number | null | undefined) {
  if (v == null) return '—';
  return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function AllocationPie({ holdings }: { holdings: PortfolioHolding[] }) {
  const valued = holdings
    .filter((h) => h.market_value != null && h.market_value > 0)
    .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0));
  if (valued.length === 0) return null;

  // Fold beyond 6 slices into "其他" (fixed hue order, never cycled).
  const top = valued.slice(0, PIE_COLORS.length);
  const rest = valued.slice(PIE_COLORS.length);
  const data = top.map((h, i) => ({
    name: h.name,
    value: h.market_value ?? 0,
    color: PIE_COLORS[i],
  }));
  if (rest.length > 0) {
    data.push({
      name: '其他',
      value: rest.reduce((s, h) => s + (h.market_value ?? 0), 0),
      color: OTHER_COLOR,
    });
  }
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <CardTitle className="text-base text-white">資產配置</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-4 sm:flex-row">
          <ResponsiveContainer width={180} height={180}>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                innerRadius={48}
                outerRadius={82}
                stroke="#0f172a"
                strokeWidth={2}
                isAnimationActive={false}
              >
                {data.map((d) => (
                  <Cell key={d.name} fill={d.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#e2e8f0',
                  fontSize: 12,
                }}
                formatter={(value, name) => [
                  `${fmtMoney(Number(value))} 元 (${((Number(value) / total) * 100).toFixed(1)}%)`,
                  String(name),
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="flex-1 space-y-1.5">
            {data.map((d) => (
              <li key={d.name} className="flex items-center gap-2 text-xs">
                <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: d.color }} />
                <span className="text-slate-300">{d.name}</span>
                <span className="ml-auto text-slate-400">
                  {((d.value / total) * 100).toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function AddHoldingForm({
  onSubmit,
  initial,
  onCancel,
}: {
  onSubmit: (stockId: string, qty: number, cost: number) => Promise<void>;
  initial?: { stockId: string; name: string; qty: number; cost: number };
  onCancel?: () => void;
}) {
  const [query, setQuery] = useState(initial ? `${initial.stockId} ${initial.name}` : '');
  const [stockId, setStockId] = useState(initial?.stockId ?? '');
  const [qty, setQty] = useState(initial ? String(initial.qty) : '');
  const [cost, setCost] = useState(initial ? String(initial.cost) : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showList, setShowList] = useState(false);
  const { data: results } = useStockSearch(showList ? query.trim() : '');

  async function submit() {
    const q = parseInt(qty, 10);
    const c = parseFloat(cost);
    if (!stockId) return setError('請先從搜尋結果選擇股票');
    if (!q || q <= 0) return setError('股數需為正整數');
    if (!c || c <= 0) return setError('成本需為正數');
    setBusy(true);
    setError('');
    try {
      await onSubmit(stockId, q, c);
      setQuery(''); setStockId(''); setQty(''); setCost('');
      onCancel?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : '儲存失敗');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="grid gap-3 sm:grid-cols-[1fr_110px_110px_auto]">
        <div className="relative">
          <Input
            value={query}
            disabled={!!initial}
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
        <Input
          value={qty}
          onChange={(e) => setQty(e.target.value.replace(/[^0-9]/g, ''))}
          placeholder="股數"
          inputMode="numeric"
          className="border-slate-700 bg-slate-800 text-sm text-white placeholder:text-slate-500"
        />
        <Input
          value={cost}
          onChange={(e) => setCost(e.target.value.replace(/[^0-9.]/g, ''))}
          placeholder="平均成本"
          inputMode="decimal"
          className="border-slate-700 bg-slate-800 text-sm text-white placeholder:text-slate-500"
        />
        <div className="flex gap-2">
          <button
            onClick={submit}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/30 disabled:opacity-60"
          >
            <Plus className="h-4 w-4" /> {initial ? '更新' : '新增'}
          </button>
          {onCancel && (
            <button onClick={onCancel} className="rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white">
              取消
            </button>
          )}
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      <p className="mt-2 text-[10px] text-slate-500">單位為「股」(1 張 = 1000 股)。同一檔重複新增會覆蓋原本的股數與成本。</p>
    </div>
  );
}

export default function PortfolioPage() {
  const { holdings, loading, loggedIn, upsert, remove } = usePortfolio();
  const router = useRouter();
  const [editing, setEditing] = useState<string | null>(null);

  const totalCost = holdings.reduce((s, h) => s + h.cost_value, 0);
  const totalValue = holdings.reduce((s, h) => s + (h.market_value ?? h.cost_value), 0);
  const totalPnl = totalValue - totalCost;
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  if (!loggedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-10 text-center">
          <Briefcase className="mx-auto mb-3 h-8 w-8 text-slate-600" />
          <p className="mb-4 text-sm text-slate-400">登入後即可記錄持股,追蹤損益與資產配置。</p>
          <button
            onClick={() => router.push('/login')}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-500/30"
          >
            <LogIn className="h-4 w-4" /> 登入 / 註冊
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <Briefcase className="h-6 w-6 text-emerald-400" /> 投資組合
          </h1>
          <p className="mt-1 text-sm text-slate-400">記錄持股成本,自動追蹤市值與損益(紅賺綠賠)。</p>
        </div>

        {/* Summary tiles */}
        {holdings.length > 0 && (
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Card className="border-slate-800 bg-slate-900">
              <CardContent className="p-4">
                <div className="text-xs text-slate-400">總市值</div>
                <div className="mt-1 text-xl font-bold text-white">{fmtMoney(totalValue)}</div>
              </CardContent>
            </Card>
            <Card className="border-slate-800 bg-slate-900">
              <CardContent className="p-4">
                <div className="text-xs text-slate-400">總成本</div>
                <div className="mt-1 text-xl font-bold text-white">{fmtMoney(totalCost)}</div>
              </CardContent>
            </Card>
            <Card className="border-slate-800 bg-slate-900">
              <CardContent className="p-4">
                <div className="text-xs text-slate-400">未實現損益</div>
                <div className={`mt-1 text-xl font-bold ${changeTextClass(totalPnl)}`}>
                  {totalPnl >= 0 ? '+' : ''}{fmtMoney(totalPnl)}
                </div>
              </CardContent>
            </Card>
            <Card className="border-slate-800 bg-slate-900">
              <CardContent className="p-4">
                <div className="text-xs text-slate-400">報酬率</div>
                <div className={`mt-1 text-xl font-bold ${changeTextClass(totalPnlPct)}`}>
                  {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="mb-6">
          <AddHoldingForm onSubmit={upsert} />
        </div>

        {loading ? (
          <Skeleton className="h-40 w-full bg-slate-800" />
        ) : holdings.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">尚無持股,從上方搜尋新增第一筆。</p>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            {/* Holdings table */}
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-left text-xs text-slate-400">
                    <th className="px-4 py-3 font-normal">股票</th>
                    <th className="px-3 py-3 text-right font-normal">股數</th>
                    <th className="px-3 py-3 text-right font-normal">成本</th>
                    <th className="px-3 py-3 text-right font-normal">現價</th>
                    <th className="px-3 py-3 text-right font-normal">損益</th>
                    <th className="px-3 py-3 text-right font-normal">報酬率</th>
                    <th className="px-3 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.stock_id} className="border-b border-slate-800/60 last:border-0">
                      <td className="px-4 py-3">
                        <Link href={`/stock/?id=${h.stock_id}`} className="hover:text-emerald-300">
                          <span className="font-medium text-white">{h.name}</span>
                          <span className="ml-1.5 font-mono text-xs text-slate-500">{h.stock_id}</span>
                        </Link>
                      </td>
                      <td className="px-3 py-3 text-right text-slate-300">{h.quantity.toLocaleString()}</td>
                      <td className="px-3 py-3 text-right text-slate-300">{h.avg_cost}</td>
                      <td className="px-3 py-3 text-right text-slate-300">{h.close ?? '—'}</td>
                      <td className={`px-3 py-3 text-right font-medium ${changeTextClass(h.pnl ?? 0)}`}>
                        {h.pnl != null ? `${h.pnl >= 0 ? '+' : ''}${fmtMoney(h.pnl)}` : '—'}
                      </td>
                      <td className={`px-3 py-3 text-right ${changeTextClass(h.pnl_percent ?? 0)}`}>
                        {h.pnl_percent != null ? `${h.pnl_percent >= 0 ? '+' : ''}${h.pnl_percent.toFixed(2)}%` : '—'}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <span className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditing(editing === h.stock_id ? null : h.stock_id)}
                            title="編輯"
                            className="text-slate-500 hover:text-emerald-400"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => remove(h.stock_id)}
                            title="刪除"
                            className="text-slate-500 hover:text-red-400"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {editing && (
                <div className="border-t border-slate-800 p-3">
                  {(() => {
                    const h = holdings.find((x) => x.stock_id === editing);
                    if (!h) return null;
                    return (
                      <AddHoldingForm
                        initial={{ stockId: h.stock_id, name: h.name, qty: h.quantity, cost: h.avg_cost }}
                        onSubmit={upsert}
                        onCancel={() => setEditing(null)}
                      />
                    );
                  })()}
                </div>
              )}
            </div>

            <AllocationPie holdings={holdings} />
          </div>
        )}

        <p className="mt-6 text-center text-xs text-slate-600">
          損益依最近收盤價估算,未含手續費與交易稅。
        </p>
      </div>
    </div>
  );
}
