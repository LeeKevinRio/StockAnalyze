import useSWR from 'swr';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const fetcher = (url: string) => fetch(`${API_BASE}${url}`).then((r) => r.json());

export function useInstitutionalData(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/institutional/${stockId}` : null,
    fetcher,
  );
}

export function useMarginData(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/institutional/${stockId}/margin` : null,
    fetcher,
  );
}

export function useInstitutionalSummary(stockId: string | null) {
  return useSWR(
    stockId ? `/api/v1/institutional/${stockId}/summary` : null,
    fetcher,
  );
}
