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
  HotStockDetailed,
  AnalysisScores,
  AnalysisReport,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

function authHeader(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }

  return res.json();
}

// Auth APIs
export interface AuthToken { access_token: string; token_type: string; email: string }
export const authAPI = {
  register: (email: string, password: string) =>
    fetchAPI<AuthToken>(`/api/v1/auth/register`, { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    fetchAPI<AuthToken>(`/api/v1/auth/login`, { method: 'POST', body: JSON.stringify({ email, password }) }),
  google: (credential: string) =>
    fetchAPI<AuthToken>(`/api/v1/auth/google`, { method: 'POST', body: JSON.stringify({ credential }) }),
  me: () => fetchAPI<{ id: number; email: string }>(`/api/v1/auth/me`),
};

// Watchlist APIs (require auth)
export const watchlistAPI = {
  get: () => fetchAPI<string[]>(`/api/v1/watchlist`),
  add: (id: string) => fetchAPI<{ ok: boolean }>(`/api/v1/watchlist/${id}`, { method: 'POST' }),
  remove: (id: string) => fetchAPI<{ ok: boolean }>(`/api/v1/watchlist/${id}`, { method: 'DELETE' }),
};

// Stock APIs
export const stockAPI = {
  search: (q: string) => fetchAPI<StockSearchResult[]>(`/api/v1/stocks/search?q=${encodeURIComponent(q)}`),
  getDetail: (id: string) => fetchAPI<StockDetail>(`/api/v1/stocks/${id}`),
  getPrices: (id: string, days = 60) => fetchAPI<StockPrice[]>(`/api/v1/stocks/${id}/prices?days=${days}`),
  getHot: () => fetchAPI<StockSearchResult[]>(`/api/v1/stocks/hot`),
  getHotDetailed: (limit = 8) => fetchAPI<HotStockDetailed[]>(`/api/v1/stocks/hot-detailed?limit=${limit}`),
  getBatch: (ids: string[]) => fetchAPI<HotStockDetailed[]>(`/api/v1/stocks/batch?ids=${encodeURIComponent(ids.join(','))}`),
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
  refresh: (id: string) => fetchAPI<AnalysisReport>(`/api/v1/analysis/${id}/refresh`, { method: 'POST' }),
};
