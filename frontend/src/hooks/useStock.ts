import useSWR from 'swr';
import { stockAPI } from '@/lib/api';

export function useStockDetail(stockId: string | null) {
  return useSWR(
    stockId ? `/stock/${stockId}` : null,
    () => stockAPI.getDetail(stockId!),
  );
}

export function useStockPrices(stockId: string | null, days = 60) {
  return useSWR(
    stockId ? `/stock/${stockId}/prices/${days}` : null,
    () => stockAPI.getPrices(stockId!, days),
  );
}

export function useHotStocksDetailed(limit = 8) {
  return useSWR(`/stocks/hot-detailed/${limit}`, () => stockAPI.getHotDetailed(limit));
}

export function useStockSearch(query: string) {
  return useSWR(
    query.length >= 1 ? `/stock/search/${query}` : null,
    () => stockAPI.search(query),
    { dedupingInterval: 300 },
  );
}
