import useSWR from 'swr';
import { analysisAPI, macroAPI, reportsAPI, sentimentAPI, type ScreenerParams } from '@/lib/api';

export function useAnalysisScores(stockId: string | null) {
  return useSWR(
    stockId ? `/analysis/${stockId}/scores` : null,
    () => analysisAPI.getScores(stockId!),
  );
}

export function useAnalysisReport(stockId: string | null) {
  return useSWR(
    stockId ? `/analysis/${stockId}/report` : null,
    () => analysisAPI.getReport(stockId!),
  );
}

export function useSentimentSummary(stockId: string | null) {
  return useSWR(
    stockId ? `/sentiment/${stockId}` : null,
    () => sentimentAPI.getSummary(stockId!),
  );
}

export function useSocialPosts(stockId: string | null) {
  return useSWR(
    stockId ? `/sentiment/${stockId}/social` : null,
    () => sentimentAPI.getSocialPosts(stockId!),
  );
}

export function useHotStocks() {
  return useSWR('/sentiment/hot-stocks', () => sentimentAPI.getHotStocks());
}

export function useScreener(params: ScreenerParams) {
  const key = `/analysis/screener/${params.signal ?? 'all'}/${params.sort ?? 'overall'}/${params.limit ?? 20}`;
  return useSWR(key, () => analysisAPI.screen(params), { revalidateOnFocus: false });
}

export function useMacroDashboard() {
  return useSWR('/macro/dashboard', () => macroAPI.getDashboard(), { revalidateOnFocus: false });
}

export function useRecentReports(limit = 50) {
  return useSWR(`/analysis/reports/recent/${limit}`, () => reportsAPI.getRecent(limit), {
    revalidateOnFocus: false,
  });
}

export function useScoreHistory(stockId: string | null, days = 90) {
  return useSWR(
    stockId ? `/analysis/${stockId}/history/${days}` : null,
    () => reportsAPI.getHistory(stockId!, days),
    { revalidateOnFocus: false },
  );
}
