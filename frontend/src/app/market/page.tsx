'use client';

import Link from 'next/link';
import { LineChart, Flame, ArrowRight, Activity } from 'lucide-react';
import { useMacroDashboard } from '@/hooks/useAnalysis';
import { useHotStocksDetailed } from '@/hooks/useStock';
import { useMarketNews } from '@/hooks/useNews';
import { StockQuoteCard } from '@/components/stock/StockQuoteCard';
import { NewsCard } from '@/components/news/NewsCard';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { scoreTextClass, changeTextClass } from '@/lib/marketColors';
import type { HotStockDetailed, MacroIndicatorItem } from '@/lib/types';

const CYCLE_LABEL: Record<string, string> = {
  expansion: '擴張', contraction: '收縮', recovery: '復甦', slowdown: '趨緩',
  cutting: '降息循環', hiking: '升息循環', holding: '利率持平',
};

function IndicatorTile({
  label, item, suffix = '', invert = false,
}: { label: string; item: MacroIndicatorItem | null; suffix?: string; invert?: boolean }) {
  const value = item?.value;
  const change = item?.change ?? 0;
  // invert=true → a falling value is "good"/bullish (e.g. VIX, exchange rate for exporters is context-specific; keep neutral colouring on change direction)
  const colorVal = invert ? -change : change;
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardContent className="p-4">
        <div className="text-xs text-slate-400">{label}</div>
        <div className="mt-1 text-xl font-bold text-white">
          {value != null ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : '—'}
          {value != null && suffix && <span className="ml-0.5 text-xs font-normal text-slate-500">{suffix}</span>}
        </div>
        {item?.change != null && (
          <div className={`mt-0.5 text-xs ${changeTextClass(colorVal)}`}>
            {change >= 0 ? '+' : ''}{change.toLocaleString('en-US', { maximumFractionDigits: 2 })}
            {item.trend ? `（${item.trend === 'rising' ? '上升' : item.trend === 'falling' ? '下降' : '持平'}）` : ''}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function MarketPage() {
  const { data: macro, isLoading: macroLoading } = useMacroDashboard();
  const { data: hot, isLoading: hotLoading } = useHotStocksDetailed(8);
  const { data: news, isLoading: newsLoading } = useMarketNews(8);

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <LineChart className="h-6 w-6 text-emerald-400" /> 市場總覽
          </h1>
          <p className="mt-1 text-sm text-slate-400">大盤指數、總經環境、熱門股與即時消息一頁掌握。</p>
        </div>

        {/* Macro score banner */}
        {macroLoading ? (
          <Skeleton className="mb-6 h-28 w-full bg-slate-800" />
        ) : macro ? (
          <Card className="mb-6 border-slate-800 bg-gradient-to-br from-slate-900 to-slate-900/40">
            <CardContent className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <Activity className="h-8 w-8 text-emerald-400" />
                  <div>
                    <div className="text-xs text-slate-400">總經環境評分</div>
                    <div className={`text-3xl font-bold ${scoreTextClass(macro.score)}`}>
                      {macro.score >= 0 ? '+' : ''}{Math.round(macro.score)}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {macro.business_cycle && (
                    <span className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-300">
                      景氣：{CYCLE_LABEL[macro.business_cycle] ?? macro.business_cycle}
                    </span>
                  )}
                  {macro.rate_cycle && (
                    <span className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-300">
                      {CYCLE_LABEL[macro.rate_cycle] ?? macro.rate_cycle}
                    </span>
                  )}
                </div>
              </div>
              {macro.summary && (
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{macro.summary}</p>
              )}
            </CardContent>
          </Card>
        ) : null}

        {/* Indicator grid */}
        {macro && (
          <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <IndicatorTile label="加權指數 TAIEX" item={macro.taiex} />
            <IndicatorTile label="美元/台幣" item={macro.exchange_rate} />
            <IndicatorTile label="美國利率" item={macro.interest_rate} suffix="%" />
            <IndicatorTile label="台灣利率" item={macro.taiwan_rate} suffix="%" />
            <IndicatorTile label="VIX 恐慌指數" item={macro.vix} invert />
            <IndicatorTile label="美十年債" item={macro.ten_year_treasury} suffix="%" />
          </div>
        )}

        {/* Hot stocks */}
        <section className="mb-10">
          <div className="mb-4 flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-400" />
            <h2 className="text-lg font-semibold text-white">熱門股</h2>
          </div>
          {hotLoading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-32 w-full bg-slate-800" />
              ))}
            </div>
          ) : hot && hot.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {hot.map((s: HotStockDetailed) => (
                <StockQuoteCard key={s.stock_id} stock={s} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">暫無熱門股資料</p>
          )}
        </section>

        {/* News */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">市場消息</h2>
            <Link href="/news" className="flex items-center gap-1 text-sm text-emerald-400 hover:text-emerald-300">
              更多新聞 <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          {newsLoading ? (
            <div className="grid gap-3 md:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full bg-slate-800" />
              ))}
            </div>
          ) : news && news.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {news.map((n) => <NewsCard key={n.id} news={n} />)}
            </div>
          ) : (
            <p className="text-sm text-slate-500">暫無新聞資料</p>
          )}
        </section>
      </div>
    </div>
  );
}
