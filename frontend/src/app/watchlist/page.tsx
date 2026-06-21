'use client';

import useSWR from 'swr';
import Link from 'next/link';
import { Star, Search } from 'lucide-react';
import { stockAPI } from '@/lib/api';
import { useWatchlist } from '@/hooks/useWatchlist';
import { StockQuoteCard } from '@/components/stock/StockQuoteCard';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function WatchlistPage() {
  const { ids } = useWatchlist();
  const { data, isLoading } = useSWR(
    ids.length ? `/batch/${ids.join(',')}` : null,
    () => stockAPI.getBatch(ids),
  );

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <header className="mb-6 flex items-center gap-2">
          <Star className="h-6 w-6 text-amber-400" fill="currentColor" />
          <h1 className="text-2xl font-bold text-white">自選股</h1>
          {ids.length > 0 && <span className="text-sm text-slate-400">{ids.length} 檔</span>}
        </header>

        {ids.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900">
            <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
              <Star className="h-10 w-10 text-slate-600" />
              <div>
                <p className="text-white">還沒有自選股</p>
                <p className="mt-1 text-sm text-slate-400">在個股頁或首頁點擊 ☆ 星號，就會加入這裡。</p>
              </div>
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
              >
                <Search className="h-4 w-4" /> 去搜尋股票
              </Link>
            </CardContent>
          </Card>
        ) : isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: Math.min(ids.length, 8) }).map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-xl bg-slate-800" />
            ))}
          </div>
        ) : data && data.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {data.map((stock) => (
              <StockQuoteCard key={stock.stock_id} stock={stock} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">自選股資料載入中或暫無報價。</p>
        )}
      </div>
    </div>
  );
}
