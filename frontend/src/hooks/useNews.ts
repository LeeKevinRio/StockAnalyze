import useSWR from 'swr';
import { newsAPI } from '@/lib/api';

export function useStockNews(stockId: string | null, limit = 20) {
  return useSWR(
    stockId ? `/news/${stockId}` : null,
    () => newsAPI.getStockNews(stockId!, limit),
  );
}

export function useMarketNews(limit = 20) {
  return useSWR('/news/market', () => newsAPI.getMarketNews(limit));
}

export function useNewsSentimentTrend(stockId: string | null, days = 30) {
  return useSWR(
    stockId ? `/news/${stockId}/sentiment-trend` : null,
    () => newsAPI.getSentimentTrend(stockId!, days),
  );
}
