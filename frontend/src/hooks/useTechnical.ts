import useSWR from 'swr';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const fetcher = (url: string) => fetch(`${API_BASE}${url}`).then((r) => r.json());

export function useTechnicalIndicators(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/technical/${stockId}` : null,
    fetcher,
  );
}
