'use client';

import { useStockPrices } from '@/hooks/useStock';
import { changeTextClass } from '@/lib/marketColors';

/** Tiny inline sparkline for a series of numbers. */
function Sparkline({ values, up }: { values: number[]; up: boolean }) {
  if (values.length < 2) return null;
  const w = 200;
  const h = 36;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  // Taiwan: up = red, down = green
  const stroke = up ? '#ef4444' : '#22c55e';
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-9 w-full">
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}

export function MarketIndexWidget() {
  // TAIEX (加權指數) is stored under the "TAIEX" symbol.
  const { data: prices } = useStockPrices('TAIEX', 30);

  const sorted = Array.isArray(prices)
    ? [...prices].sort((a, b) => a.date.localeCompare(b.date))
    : [];
  const closes = sorted.map((p) => Number(p.close)).filter((n) => !Number.isNaN(n));
  const hasData = closes.length >= 2;

  const latest = hasData ? closes[closes.length - 1] : null;
  const prev = hasData ? closes[closes.length - 2] : null;
  const change = latest != null && prev != null ? latest - prev : null;
  const changePct = change != null && prev ? (change / prev) * 100 : null;
  const up = (change ?? 0) >= 0;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-300">加權指數</span>
        <span className="text-[10px] text-slate-500">TAIEX</span>
      </div>

      {hasData ? (
        <>
          <div className="text-lg font-bold text-white">
            {latest!.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className={`text-xs font-medium ${changeTextClass(change ?? 0)}`}>
            {up ? '+' : ''}{change!.toFixed(2)} ({up ? '+' : ''}{changePct!.toFixed(2)}%)
          </div>
          <div className="mt-1">
            <Sparkline values={closes} up={up} />
          </div>
        </>
      ) : (
        <div className="py-2 text-xs text-slate-500">資料待接入</div>
      )}
    </div>
  );
}
