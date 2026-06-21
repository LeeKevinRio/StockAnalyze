'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, TrendingUp, Flame, ArrowRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { NewsCard } from '@/components/news/NewsCard';
import { StockQuoteCard } from '@/components/stock/StockQuoteCard';
import { useMarketNews } from '@/hooks/useNews';
import { useStockSearch, useHotStocksDetailed } from '@/hooks/useStock';
import type { HotStockDetailed } from '@/lib/types';

export default function HomePage() {
  const router = useRouter();
  const { data: hotStocks, isLoading: hotLoading } = useHotStocksDetailed(8);
  const { data: marketNews, isLoading: newsLoading } = useMarketNews(10);

  // Hero search state
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: searchResults } = useStockSearch(debouncedQuery);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleSelect(stockId: string) {
    setIsOpen(false);
    setQuery('');
    router.push(`/stock/?id=${stockId}`);
  }

  const todayStr = new Date().toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 px-4 py-16 md:py-24">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 flex items-center justify-center gap-2">
            <TrendingUp className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="mb-3 text-3xl font-bold tracking-tight text-white md:text-5xl">
            台股分析平台
          </h1>
          <p className="mb-8 text-sm text-slate-400 md:text-base">
            五維度深度分析 - 消息面・基本面・技術面・籌碼面・總經面
          </p>

          {/* Hero Search Input */}
          <div ref={containerRef} className="relative mx-auto max-w-xl">
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <Input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setIsOpen(true);
                }}
                onFocus={() => setIsOpen(true)}
                placeholder="輸入股票代號或名稱，例如: 2330 台積電"
                className="h-12 rounded-xl border-slate-700 bg-slate-800/80 pl-12 text-base text-white placeholder:text-slate-500 focus-visible:border-emerald-500 focus-visible:ring-emerald-500/30 md:text-lg"
              />
            </div>

            {isOpen && searchResults && searchResults.length > 0 && (
              <ul className="absolute left-0 right-0 top-full z-50 mt-2 max-h-72 overflow-y-auto rounded-xl border border-slate-700 bg-slate-800 py-1 shadow-2xl">
                {searchResults.map((item) => (
                  <li key={item.stock_id}>
                    <button
                      type="button"
                      onClick={() => handleSelect(item.stock_id)}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:bg-slate-700"
                    >
                      <span className="font-mono font-semibold text-emerald-400">
                        {item.stock_id}
                      </span>
                      <span className="truncate text-white">{item.name}</span>
                      {item.industry && (
                        <span className="ml-auto shrink-0 text-xs text-slate-400">
                          {item.industry}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Market Sentiment Section */}
        <section className="mb-10">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-orange-400" />
              <h2 className="text-lg font-semibold text-white">熱門股</h2>
              <span className="text-sm text-slate-400">{todayStr}</span>
            </div>
          </div>

          {hotLoading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Card key={i} className="border-slate-800 bg-slate-900">
                  <CardContent className="space-y-2">
                    <Skeleton className="h-4 w-16 bg-slate-700" />
                    <Skeleton className="h-6 w-24 bg-slate-700" />
                    <Skeleton className="h-9 w-full bg-slate-700" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : hotStocks && hotStocks.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {hotStocks.map((stock: HotStockDetailed) => (
                <StockQuoteCard key={stock.stock_id} stock={stock} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">暫無熱門股票資料</p>
          )}
        </section>

        {/* Latest News Section */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">最新消息</h2>
            <Link
              href="/news"
              className="flex items-center gap-1 text-sm text-emerald-400 transition-colors hover:text-emerald-300"
            >
              更多新聞
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {newsLoading ? (
            <div className="grid gap-3 md:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="border-slate-800 bg-slate-900">
                  <CardContent className="space-y-2">
                    <Skeleton className="h-4 w-3/4 bg-slate-700" />
                    <Skeleton className="h-3 w-1/2 bg-slate-700" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : marketNews && marketNews.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {marketNews.slice(0, 10).map((news) => (
                <NewsCard key={news.id} news={news} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">暫無新聞資料</p>
          )}
        </section>
      </div>
    </div>
  );
}
