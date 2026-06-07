'use client';

import { Newspaper } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { NewsCard } from '@/components/news/NewsCard';
import { useMarketNews } from '@/hooks/useNews';

export default function NewsPage() {
  const { data: news, isLoading } = useMarketNews(50);

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-4xl px-4 py-8">
        {/* Page Header */}
        <div className="mb-6 flex items-center gap-3">
          <Newspaper className="h-6 w-6 text-emerald-400" />
          <h1 className="text-2xl font-bold text-white">市場新聞</h1>
        </div>

        {/* News Feed */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} className="border-slate-800 bg-slate-900">
                <CardContent className="space-y-2">
                  <Skeleton className="h-4 w-3/4 bg-slate-700" />
                  <Skeleton className="h-3 w-1/2 bg-slate-700" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : news && news.length > 0 ? (
          <div className="space-y-3">
            {news.map((item) => (
              <NewsCard key={item.id} news={item} />
            ))}
          </div>
        ) : (
          <Card className="border-slate-800 bg-slate-900">
            <CardContent className="py-10 text-center text-slate-400">
              暫無新聞資料
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
