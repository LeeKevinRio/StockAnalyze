import useSWR from 'swr';
import { analysisAPI, sentimentAPI } from '@/lib/api';

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
