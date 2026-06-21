'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Star } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Sparkline } from '@/components/common/Sparkline';
import { changeTextClass } from '@/lib/marketColors';
import { useWatchlist } from '@/hooks/useWatchlist';
import type { HotStockDetailed } from '@/lib/types';

function signalLabel(signal: string | null): { label: string; cls: string } | null {
  if (!signal) return null;
  // Taiwan convention: 買進/看多 = red, 賣出/看空 = green.
  if (signal === 'strong_buy' || signal === 'buy' || signal === 'bullish')
    return { label: '買進', cls: 'bg-red-500/15 text-red-400 border-red-500/30' };
  if (signal === 'sell' || signal === 'strong_sell' || signal === 'bearish')
    return { label: '賣出', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' };
  return { label: '中性', cls: 'bg-slate-500/15 text-slate-400 border-slate-600/40' };
}

export function StockQuoteCard({ stock }: { stock: HotStockDetailed }) {
  const router = useRouter();
  const { has, toggle, loggedIn } = useWatchlist();
  const up = stock.change >= 0;
  const sig = signalLabel(stock.signal);
  const starred = has(stock.stock_id);

  return (
    <Card className="border-slate-800 bg-slate-900 transition-colors hover:border-emerald-500/40 hover:bg-slate-800/80">
      <CardContent className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <Link href={`/stock?id=${stock.stock_id}`} className="flex min-w-0 flex-1 items-baseline gap-2">
            <span className="truncate text-sm font-medium text-white">{stock.name}</span>
            <span className="shrink-0 font-mono text-xs text-slate-500">{stock.stock_id}</span>
          </Link>
          <button
            onClick={() => { if (loggedIn) toggle(stock.stock_id); else router.push('/login'); }}
            title={loggedIn ? (starred ? '移除自選' : '加入自選') : '登入後加入自選'}
            className={`shrink-0 transition-colors ${starred ? 'text-amber-400' : 'text-slate-600 hover:text-amber-400'}`}
          >
            <Star className="h-4 w-4" fill={starred ? 'currentColor' : 'none'} />
          </button>
        </div>
        <Link href={`/stock?id=${stock.stock_id}`} className="block space-y-2">
          <div>
            <div className="text-xl font-bold text-white">
              {stock.close.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className={`text-xs font-medium ${changeTextClass(stock.change)}`}>
              {up ? '+' : ''}{stock.change.toFixed(2)} ({up ? '+' : ''}{stock.change_percent.toFixed(2)}%)
            </div>
          </div>
          <Sparkline values={stock.sparkline} up={up} className="h-9 w-full" />
          {sig && (
            <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${sig.cls}`}>
              {sig.label}
            </span>
          )}
        </Link>
      </CardContent>
    </Card>
  );
}
