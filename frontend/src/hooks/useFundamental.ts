import useSWR from 'swr';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const fetcher = (url: string) => fetch(`${API_BASE}${url}`).then((r) => r.json());

export function useFundamentalData(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/fundamental/${stockId}` : null,
    fetcher,
  );
}

export function useFinancialStatements(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/fundamental/${stockId}/financials` : null,
    fetcher,
  );
}

export function useDividends(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/fundamental/${stockId}/dividends` : null,
    fetcher,
  );
}

export function usePeers(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/fundamental/${stockId}/peers` : null,
    fetcher,
  );
}
