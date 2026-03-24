'use client';

import type { NewsItem } from '@/lib/types';
import { Card, CardContent } from '@/components/ui/card';
import { SentimentBadge } from './SentimentBadge';

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return '剛剛';
  if (diffMin < 60) return `${diffMin}分鐘前`;
  if (diffHr < 24) return `${diffHr}小時前`;
  if (diffDay < 30) return `${diffDay}天前`;
  return new Date(dateStr).toLocaleDateString('zh-TW');
}

interface NewsCardProps {
  news: NewsItem;
}

export function NewsCard({ news }: NewsCardProps) {
  const handleClick = () => {
    if (news.source_url) {
      window.open(news.source_url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <Card
      className="cursor-pointer transition-shadow hover:ring-2 hover:ring-emerald-500/30"
      onClick={handleClick}
    >
      <CardContent className="flex flex-col gap-2">
        {/* Title row */}
        <div className="flex items-start gap-2">
          {/* Impact level indicator */}
          {news.impact_level === 'high' && (
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500" />
          )}
          {news.impact_level === 'medium' && (
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-yellow-500" />
          )}
          <h3 className="line-clamp-2 flex-1 text-sm font-medium leading-snug">
            {news.title}
          </h3>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {news.source && <span>{news.source}</span>}
          {news.published_at && (
            <>
              {news.source && <span>·</span>}
              <span>{formatRelativeTime(news.published_at)}</span>
            </>
          )}
          <div className="ml-auto">
            <SentimentBadge
              sentiment={news.sentiment}
              score={news.sentiment_score}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
