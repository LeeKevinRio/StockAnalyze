import type {
  StockSearchResult,
  StockDetail,
  StockPrice,
  NewsItem,
  SentimentTrendPoint,
  SentimentSummary,
  SentimentTrend,
  SocialPost,
  HotStock,
  AnalysisScores,
  AnalysisReport,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Stock APIs
export const stockAPI = {
  search: (q: string) => fetchAPI<StockSearchResult[]>(`/api/v1/stocks/search?q=${encodeURIComponent(q)}`),
  getDetail: (id: string) => fetchAPI<StockDetail>(`/api/v1/stocks/${id}`),
  getPrices: (id: string, days = 60) => fetchAPI<StockPrice[]>(`/api/v1/stocks/${id}/prices?days=${days}`),
  getHot: () => fetchAPI<StockSearchResult[]>(`/api/v1/stocks/hot`),
};

// News APIs
export const newsAPI = {
  getMarketNews: (limit = 20) => fetchAPI<NewsItem[]>(`/api/v1/news/market?limit=${limit}`),
  getStockNews: (id: string, limit = 20) => fetchAPI<NewsItem[]>(`/api/v1/news/${id}?limit=${limit}`),
  getSentimentTrend: (id: string, days = 30) => fetchAPI<SentimentTrendPoint[]>(`/api/v1/news/${id}/sentiment-trend?days=${days}`),
};

// Sentiment APIs
export const sentimentAPI = {
  getSummary: (id: string) => fetchAPI<SentimentSummary>(`/api/v1/sentiment/${id}`),
  getTrend: (id: string, days = 30) => fetchAPI<SentimentTrend[]>(`/api/v1/sentiment/${id}/trend?days=${days}`),
  getSocialPosts: (id: string) => fetchAPI<SocialPost[]>(`/api/v1/sentiment/${id}/social`),
  getHotStocks: () => fetchAPI<HotStock[]>(`/api/v1/sentiment/hot-stocks`),
};

// Analysis APIs
export const analysisAPI = {
  getScores: (id: string) => fetchAPI<AnalysisScores>(`/api/v1/analysis/${id}/scores`),
  getReport: (id: string) => fetchAPI<AnalysisReport>(`/api/v1/analysis/${id}/report`),
};
