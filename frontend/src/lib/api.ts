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
  ScreenerPick,
  MacroDashboard,
  ReportSummary,
  ScoreHistoryPoint,
  PortfolioHolding,
  PriceAlertItem,
  BacktestResult,
} from './types';

export interface ScreenerParams {
  limit?: number;
  signal?: string;
  sort?: string;
}

function screenerQuery(p: ScreenerParams = {}): string {
  const qs = new URLSearchParams();
  if (p.limit) qs.set('limit', String(p.limit));
  if (p.signal && p.signal !== 'all') qs.set('signal', p.signal);
  if (p.sort) qs.set('sort', p.sort);
  const s = qs.toString();
  return s ? `?${s}` : '';
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  screen: (p: ScreenerParams = {}) => fetchAPI<ScreenerPick[]>(`/api/v1/analysis/screener${screenerQuery(p)}`),
  refreshScreener: (p: ScreenerParams = {}) =>
    fetchAPI<ScreenerPick[]>(`/api/v1/analysis/screener/refresh${screenerQuery(p)}`, { method: 'POST' }),
};

// Macro APIs
export const macroAPI = {
  getDashboard: () => fetchAPI<MacroDashboard>(`/api/v1/macro/dashboard`),
};

// Health
export const healthAPI = {
  check: () => fetchAPI<{ status: string; service: string }>(`/health`),
};

// Report center APIs
export const reportsAPI = {
  getRecent: (limit = 50) => fetchAPI<ReportSummary[]>(`/api/v1/analysis/reports/recent?limit=${limit}`),
  getHistory: (id: string, days = 90) => fetchAPI<ScoreHistoryPoint[]>(`/api/v1/analysis/${id}/history?days=${days}`),
};

// Portfolio APIs (require auth)
export const portfolioAPI = {
  get: () => fetchAPI<PortfolioHolding[]>(`/api/v1/portfolio`),
  upsert: (id: string, quantity: number, avgCost: number) =>
    fetchAPI<{ ok: boolean }>(`/api/v1/portfolio/${id}`, {
      method: 'POST',
      body: JSON.stringify({ quantity, avg_cost: avgCost }),
    }),
  remove: (id: string) => fetchAPI<{ ok: boolean }>(`/api/v1/portfolio/${id}`, { method: 'DELETE' }),
};

// Backtest API
export const backtestAPI = {
  run: (id: string, strategy: 'ma_cross' | 'rsi', days: number, fast = 5, slow = 20) =>
    fetchAPI<BacktestResult>(
      `/api/v1/backtest/${id}?strategy=${strategy}&days=${days}&fast=${fast}&slow=${slow}`,
    ),
};

// Price alert APIs (require auth, except check)
export const alertsAPI = {
  get: () => fetchAPI<PriceAlertItem[]>(`/api/v1/alerts`),
  create: (stockId: string, condition: 'above' | 'below', targetPrice: number) =>
    fetchAPI<{ ok: boolean }>(`/api/v1/alerts`, {
      method: 'POST',
      body: JSON.stringify({ stock_id: stockId, condition, target_price: targetPrice }),
    }),
  remove: (id: number) => fetchAPI<{ ok: boolean }>(`/api/v1/alerts/${id}`, { method: 'DELETE' }),
};
