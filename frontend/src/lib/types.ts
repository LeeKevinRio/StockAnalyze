export interface StockSearchResult {
  stock_id: string;
  name: string;
  industry: string | null;
  market: string;
}

export interface StockPrice {
  stock_id: string;
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  change_percent: number | null;
}

export interface StockDetail {
  stock: StockSearchResult;
  latest_price: StockPrice | null;
  price_change: number | null;
  price_change_percent: number | null;
}

export interface NewsItem {
  id: number;
  stock_id: string | null;
  title: string;
  summary: string | null;
  source: string | null;
  source_url: string | null;
  sentiment: 'positive' | 'negative' | 'neutral' | null;
  sentiment_score: number | null;
  impact_level: 'high' | 'medium' | 'low' | null;
  published_at: string | null;
}

export interface SentimentTrendPoint {
  date: string;
  sentiment_score: number;
  article_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface SentimentSummary {
  stock_id: string;
  date: string;
  news_sentiment: number | null;
  social_sentiment: number | null;
  combined_sentiment: number | null;
  mention_count: number;
  heat_level: string | null;
}

export interface SentimentTrend {
  date: string;
  score: number;
  source_type: string;
  mention_count: number;
}

export interface SocialPost {
  id: number;
  platform: string;
  title: string;
  author: string | null;
  sentiment: string | null;
  sentiment_score: number | null;
  push_count: number;
  boo_count: number;
  posted_at: string | null;
  url: string | null;
}

export interface HotStock {
  stock_id: string;
  stock_name: string;
  mention_count: number;
  sentiment_score: number;
  heat_level: string;
}

export interface DimensionScore {
  name: string;
  score: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  key_factors: string[];
}

export interface HotStockDetailed {
  stock_id: string;
  name: string;
  close: number;
  change: number;
  change_percent: number;
  signal: string | null;
  sparkline: number[];
}

export interface AnalysisScores {
  stock_id: string;
  stock_name: string;
  report_date: string;
  overall_score: number;
  overall_signal: string;
  confidence: number;
  dimensions: DimensionScore[];
}

export interface ScreenerPick {
  stock_id: string;
  name: string;
  industry: string | null;
  overall_score: number;
  overall_signal: string;
  confidence: number;
  scores: {
    news: number;
    fundamental: number;
    technical: number;
    institutional: number;
    macro: number;
  };
  target_price: number | null;
  report_date: string | null;
  close: number | null;
  change_percent: number | null;
}

export interface MacroIndicatorItem {
  name: string;
  value: number | null;
  previous_value: number | null;
  change: number | null;
  trend: string | null;
  updated_at: string | null;
}

export interface MacroDashboard {
  interest_rate: MacroIndicatorItem | null;
  taiwan_rate: MacroIndicatorItem | null;
  exchange_rate: MacroIndicatorItem | null;
  taiex: MacroIndicatorItem | null;
  vix: MacroIndicatorItem | null;
  ten_year_treasury: MacroIndicatorItem | null;
  business_cycle: string | null;
  rate_cycle: string | null;
  score: number;
  summary: string | null;
  updated_at: string | null;
}

export interface ReportSummary {
  stock_id: string;
  name: string;
  report_date: string | null;
  overall_score: number;
  overall_signal: string;
  confidence: number;
  risk_level: string | null;
  target_price: number | null;
  ai_provider: string | null;
  has_full_report: boolean;
  short_term_outlook: string | null;
}

export interface ScoreHistoryPoint {
  report_date: string | null;
  overall_score: number;
  overall_signal: string;
  news: number;
  fundamental: number;
  technical: number;
  institutional: number;
  macro: number;
}

export interface PortfolioHolding {
  stock_id: string;
  name: string;
  quantity: number;
  avg_cost: number;
  close: number | null;
  cost_value: number;
  market_value: number | null;
  pnl: number | null;
  pnl_percent: number | null;
}

export interface PriceAlertItem {
  id: number;
  stock_id: string;
  name: string;
  condition: 'above' | 'below';
  target_price: number;
  active: boolean;
  close: number | null;
  triggered_at: string | null;
  triggered_price: number | null;
  created_at: string | null;
}

export interface BacktestTrade {
  date: string;
  action: 'buy' | 'sell';
  price: number;
}

export interface BacktestResult {
  stock_id: string;
  name: string;
  strategy: string;
  params: Record<string, number>;
  days: number;
  start_date: string;
  end_date: string;
  strategy_return_pct: number;
  buy_hold_return_pct: number;
  trade_count: number;
  win_rate: number | null;
  max_drawdown_pct: number;
  in_position: boolean;
  trades: BacktestTrade[];
  curve: { date: string; strategy: number; buy_hold: number }[];
}

export interface AnalysisReport {
  stock_id: string;
  stock_name: string;
  report_date: string;
  overall_score: number | null;
  overall_signal: string | null;
  confidence: number | null;
  news_score: number | null;
  fundamental_score: number | null;
  technical_score: number | null;
  institutional_score: number | null;
  macro_score: number | null;
  ai_report_markdown: string | null;
  ai_provider: string | null;
  risk_level: string | null;
  short_term_outlook: string | null;
  medium_term_outlook: string | null;
  long_term_outlook: string | null;
  target_price: number | null;
  stop_loss_price: number | null;
  created_at: string | null;
}
