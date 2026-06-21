'use client';

import { useState } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  Newspaper,
  BarChart3,
  TrendingUp,
  Users,
  Globe,
  ArrowLeft,
  Calendar,
  Shield,
  Target,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Clock,
  ArrowUpRight,
  ChevronRight,
  Info,
  TrendingDown,
  Minus,
  Star,
  Bell,
  Plus,
  Share2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { SentimentBadge } from '@/components/news/SentimentBadge';
import { NewsCard } from '@/components/news/NewsCard';
import { ScoreGauge } from '@/components/common/ScoreGauge';
import { Loading } from '@/components/common/Loading';
import { DimensionScoreCard } from '@/components/analysis/DimensionScoreCard';
import { RadarChart } from '@/components/analysis/RadarChart';
import { PriceChart } from '@/components/stock/PriceChart';
import { IndicatorPanel } from '@/components/technical/IndicatorPanel';
import { TechnicalSummary } from '@/components/technical/TechnicalSummary';
import { InstitutionalChart } from '@/components/institutional/InstitutionalChart';
import { MarginChart } from '@/components/institutional/MarginChart';
import { ChipSummary } from '@/components/institutional/ChipSummary';
import { FinancialTable } from '@/components/fundamental/FinancialTable';
import { RevenueChart } from '@/components/fundamental/RevenueChart';
import { ValuationMetrics } from '@/components/fundamental/ValuationMetrics';
import { useStockDetail, useStockPrices } from '@/hooks/useStock';
import { useStockNews } from '@/hooks/useNews';
import {
  useAnalysisScores,
  useAnalysisReport,
  useSentimentSummary,
  useSocialPosts,
} from '@/hooks/useAnalysis';
import { useTechnicalIndicators } from '@/hooks/useTechnical';
import {
  useInstitutionalData,
  useMarginData,
  useInstitutionalSummary,
} from '@/hooks/useInstitutional';
import { useFundamentalData, useFinancialStatements } from '@/hooks/useFundamental';
import { useWatchlist } from '@/hooks/useWatchlist';
import { analysisAPI } from '@/lib/api';
import type { DimensionScore } from '@/lib/types';

const DIMENSION_ICONS: Record<string, React.ElementType> = {
  '消息面': Newspaper,
  '基本面': BarChart3,
  '技術面': TrendingUp,
  '籌碼面': Users,
  '總經面': Globe,
  news: Newspaper,
  fundamental: BarChart3,
  technical: TrendingUp,
  institutional: Users,
  macro: Globe,
};

/** Map an overall signal code to a Chinese label + colour classes.
 *  Taiwan convention (紅漲綠跌): 買進/看多 = red, 賣出/看空 = green. */
function signalDisplay(signal: string | null | undefined): { label: string; text: string; bg: string; border: string } {
  switch (signal) {
    case 'strong_buy':
      return { label: '強烈買進', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' };
    case 'buy':
    case 'bullish':
      return { label: '買進 / 看多', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' };
    case 'sell':
    case 'bearish':
      return { label: '賣出 / 看空', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
    case 'strong_sell':
      return { label: '強烈賣出', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
    default:
      return { label: '中性 / 觀望', text: 'text-slate-300', bg: 'bg-slate-500/10', border: 'border-slate-600/40' };
  }
}

/** Confidence may arrive as 0-1 (e.g. 0.84) or 0-100; normalise to a percent. */
function confidencePct(c: number | null | undefined): number | null {
  if (c == null) return null;
  return c <= 1 ? Math.round(c * 100) : Math.round(c);
}

/** Map an overall score (-100..100, 0 = neutral) to a Chinese tier label + colour.
 *  Thresholds mirror the backend signal mapping. Taiwan convention (紅漲綠跌):
 *  bullish tiers = red, weak/bearish tiers = green. */
function scoreTier(score: number | null | undefined): { label: string; text: string } {
  const s = Number(score ?? 0);
  if (s >= 60) return { label: '強勢偏多', text: 'text-red-400' };
  if (s >= 20) return { label: '偏多', text: 'text-red-400' };
  if (s > -20) return { label: '中性', text: 'text-amber-400' };
  if (s > -60) return { label: '偏空', text: 'text-emerald-300' };
  return { label: '弱勢偏空', text: 'text-emerald-400' };
}

/** Confidence percent → descriptive label. */
function confidenceLabel(pct: number | null): { label: string; text: string } {
  if (pct == null) return { label: '—', text: 'text-slate-400' };
  if (pct >= 75) return { label: '信心度高', text: 'text-emerald-400' };
  if (pct >= 50) return { label: '信心度中', text: 'text-amber-400' };
  return { label: '信心度低', text: 'text-slate-400' };
}

/** Derive a 偏多/中性/偏空 tag from an outlook sentence (no fabricated data). */
function outlookTag(text: string | null | undefined): { label: string; text: string; bg: string; border: string; icon: 'up' | 'flat' | 'down' } {
  const t = text ?? '';
  const bull = /(看多|偏多|正向|樂觀|強勢|偏強|上漲|走揚|增長|成長|突破|擴張|轉強|利多)/;
  const bear = /(看空|偏空|轉弱|疲弱|下跌|回檔|修正|走低|衰退|利空|承壓|疲軟)/;
  // Taiwan convention (紅漲綠跌): 偏多 = red, 偏空 = green.
  if (bull.test(t) && !bear.test(t)) return { label: '偏多', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', icon: 'up' };
  if (bear.test(t) && !bull.test(t)) return { label: '偏空', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', icon: 'down' };
  return { label: '中性', text: 'text-sky-300', bg: 'bg-sky-500/10', border: 'border-sky-500/30', icon: 'flat' };
}

interface StockPageClientProps {
  stockId: string;
}

export default function StockPageClient({ stockId }: StockPageClientProps) {
  // Core data
  const { data: detail, isLoading: detailLoading, error: detailError } = useStockDetail(stockId);
  const { data: scores, isLoading: scoresLoading, mutate: mutateScores } = useAnalysisScores(stockId);
  const { data: report, isLoading: reportLoading, mutate: mutateReport } = useAnalysisReport(stockId);

  // Watchlist (browser-local)
  const { has: inWatchlist, toggle: toggleWatchlist } = useWatchlist();

  // AI analysis generation
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    try {
      await analysisAPI.refresh(stockId);
      await Promise.all([mutateScores(), mutateReport()]);
    } catch {
      setGenError('分析產生失敗，請確認後端服務與資料是否正常。');
    } finally {
      setGenerating(false);
    }
  }
  const { data: stockNews, isLoading: newsLoading } = useStockNews(stockId);
  const { data: sentimentSummary } = useSentimentSummary(stockId);
  const { data: socialPosts } = useSocialPosts(stockId);

  // Technical data
  const { data: stockPrices, isLoading: pricesLoading } = useStockPrices(stockId, 120);
  const { data: technicalData, isLoading: technicalLoading } = useTechnicalIndicators(stockId);

  // Institutional data
  const { data: institutionalData, isLoading: institutionalLoading } = useInstitutionalData(stockId);
  const { data: marginData, isLoading: marginLoading } = useMarginData(stockId);
  const { data: chipSummary, isLoading: chipSummaryLoading } = useInstitutionalSummary(stockId);

  // Fundamental data
  const { data: fundamentalData, isLoading: fundamentalLoading } = useFundamentalData(stockId);
  const { data: financialStatements, isLoading: statementsLoading } = useFinancialStatements(stockId);

  if (detailError) {
    return (
      <div className="min-h-screen bg-slate-950">
        <div className="mx-auto max-w-7xl px-4 py-16 text-center">
          <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-yellow-500" />
          <h1 className="mb-2 text-xl font-semibold text-white">無法載入股票資料</h1>
          <p className="mb-6 text-slate-400">
            股票代號 {stockId} 可能不存在，或伺服器暫時無法回應。
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
          >
            <ArrowLeft className="h-4 w-4" />
            返回首頁
          </Link>
        </div>
      </div>
    );
  }

  if (detailLoading) {
    return <Loading />;
  }

  const stock = detail?.stock;
  const latestPrice = detail?.latest_price;
  const closeNum = latestPrice?.close != null ? Number(latestPrice.close) : null;
  const priceChange = Number(detail?.price_change ?? 0);
  const priceChangePercent = Number(detail?.price_change_percent ?? 0);
  const isPositive = priceChange >= 0;

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-6">
        {/* Breadcrumb */}
        <nav className="mb-4 flex items-center gap-1.5 text-sm text-slate-400">
          <Link href="/" className="transition-colors hover:text-white">總覽</Link>
          <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          <span>個股</span>
          <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          <span className="text-slate-200">{stock?.name ?? stockId} ({stock?.stock_id ?? stockId})</span>
        </nav>

        <header className="mb-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            {/* Left: name, code, tags, price */}
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold text-white md:text-3xl">
                  {stock?.name ?? stockId}
                </h1>
                <span className="font-mono text-lg text-slate-400">{stock?.stock_id ?? stockId}</span>
                <button
                  onClick={() => toggleWatchlist(stockId)}
                  title={inWatchlist(stockId) ? '移除自選' : '加入自選'}
                  className={`transition-colors ${inWatchlist(stockId) ? 'text-amber-400' : 'text-slate-500 hover:text-amber-400'}`}
                >
                  <Star className="h-5 w-5" fill={inWatchlist(stockId) ? 'currentColor' : 'none'} />
                </button>
              </div>
              {/* Tag pills */}
              <div className="mb-3 flex flex-wrap items-center gap-2">
                {stock?.market && <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{stock.market === 'TWSE' ? '上市' : stock.market === 'TPEx' ? '上櫃' : stock.market}</span>}
                {stock?.industry && <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{stock.industry}</span>}
              </div>
              {closeNum != null && (
                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-bold text-white md:text-4xl">{closeNum.toFixed(2)}</span>
                  <span className={`text-lg font-medium ${isPositive ? 'text-red-400' : 'text-emerald-400'}`}>
                    {isPositive ? '+' : ''}{priceChange.toFixed(2)} ({isPositive ? '+' : ''}{priceChangePercent.toFixed(2)}%)
                  </span>
                  {latestPrice?.date && (
                    <span className="text-xs text-slate-500">收盤 {latestPrice.date}</span>
                  )}
                </div>
              )}
            </div>

            {/* Right: action buttons + overall signal badge */}
            <div className="flex flex-col items-start gap-3 lg:items-end">
              <div className="flex items-center gap-2">
                <button className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-800" title="敬請期待">
                  <Bell className="h-4 w-4" /> 設定提醒
                </button>
                <button className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-800" title="敬請期待">
                  <Plus className="h-4 w-4" /> 自選
                </button>
                <button className="inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800/60 p-2 text-slate-300 transition-colors hover:bg-slate-800" title="敬請期待">
                  <Share2 className="h-4 w-4" />
                </button>
              </div>
              {scores && (() => {
                const s = signalDisplay(scores.overall_signal);
                return (
                  <span className={`rounded-lg border px-4 py-1.5 text-lg font-bold ${s.border} ${s.bg} ${s.text}`}>
                    {s.label.split(' ')[0]}
                  </span>
                );
              })()}
            </div>
          </div>
        </header>

        <Separator className="mb-6 bg-slate-800" />

        <Tabs defaultValue="overview">
          <TabsList className="mb-6 flex-wrap bg-slate-900">
            <TabsTrigger value="overview">總覽</TabsTrigger>
            <TabsTrigger value="news">消息面</TabsTrigger>
            <TabsTrigger value="technical">技術面</TabsTrigger>
            <TabsTrigger value="fundamental">基本面</TabsTrigger>
            <TabsTrigger value="institutional">籌碼面</TabsTrigger>
            <TabsTrigger value="report">完整報告</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab
              scores={scores}
              scoresLoading={scoresLoading}
              report={report}
              latestClose={latestPrice?.close ?? null}
              generating={generating}
              genError={genError}
              onGenerate={handleGenerate}
            />
          </TabsContent>
          <TabsContent value="news">
            <NewsTab stockNews={stockNews} newsLoading={newsLoading} sentimentSummary={sentimentSummary} socialPosts={socialPosts} />
          </TabsContent>
          <TabsContent value="technical">
            <TechnicalTab prices={stockPrices} pricesLoading={pricesLoading} technicalData={technicalData} technicalLoading={technicalLoading} />
          </TabsContent>
          <TabsContent value="fundamental">
            <FundamentalTab fundamentalData={fundamentalData} fundamentalLoading={fundamentalLoading} statements={financialStatements} statementsLoading={statementsLoading} />
          </TabsContent>
          <TabsContent value="institutional">
            <InstitutionalTab institutionalData={institutionalData} institutionalLoading={institutionalLoading} marginData={marginData} marginLoading={marginLoading} chipSummary={chipSummary} chipSummaryLoading={chipSummaryLoading} />
          </TabsContent>
          <TabsContent value="report">
            <ReportTab
              report={report}
              reportLoading={reportLoading}
              generating={generating}
              genError={genError}
              onGenerate={handleGenerate}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

/* ---- Tab Components ---- */

function GenerateButton({ generating, onGenerate, hasReport }: { generating: boolean; onGenerate: () => void; hasReport: boolean }) {
  return (
    <button
      onClick={onGenerate}
      disabled={generating}
      className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {generating ? (
        <><RefreshCw className="h-4 w-4 animate-spin" /> AI 分析產生中…</>
      ) : (
        <><Sparkles className="h-4 w-4" /> {hasReport ? '重新產生 AI 分析' : '產生 AI 分析'}</>
      )}
    </button>
  );
}

function OutlookRow({ iconBg, icon, label, timeframe, text }: { iconBg: string; icon: React.ReactNode; label: string; timeframe: string; text: string }) {
  const tag = outlookTag(text);
  const TagIcon = tag.icon === 'up' ? ArrowUpRight : tag.icon === 'down' ? TrendingDown : Minus;
  return (
    <div className="flex items-center gap-4 py-3">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${iconBg}`}>{icon}</div>
      <div className="w-32 shrink-0">
        <div className="font-semibold text-white">{label}</div>
        <div className="text-xs text-slate-400">{timeframe}</div>
      </div>
      <p className="flex-1 text-sm leading-relaxed text-slate-300">{text}</p>
      <div className={`flex shrink-0 items-center gap-1 rounded-lg border px-2.5 py-1 text-sm font-medium ${tag.border} ${tag.bg} ${tag.text}`}>
        <TagIcon className="h-3.5 w-3.5" /> {tag.label}
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-500" />
    </div>
  );
}

/** A bordered metric cell used in the decision-summary top row. */
function MetricCell({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 p-4">{children}</div>;
}

function DecisionSummary({ scores, report, latestClose, reportDate, generating, onGenerate }: { scores: any; report: any; latestClose: number | null; reportDate?: string; generating: boolean; onGenerate: () => void }) {
  const sig = signalDisplay(scores?.overall_signal ?? report?.overall_signal);
  // Bullish is red under the Taiwan convention, so an up-arrow maps to red text.
  const SigIcon = sig.text.includes('red') ? ArrowUpRight : sig.text.includes('emerald') ? TrendingDown : Minus;
  const score = scores?.overall_score != null ? Number(scores.overall_score) : null;
  const tier = scoreTier(score);
  const conf = confidencePct(scores?.confidence ?? report?.confidence);
  const confLbl = confidenceLabel(conf);
  const target = report?.target_price != null ? Number(report.target_price) : null;
  const stop = report?.stop_loss_price != null ? Number(report.stop_loss_price) : null;
  const upside = target != null && latestClose != null && latestClose > 0 ? ((target - latestClose) / latestClose) * 100 : null;
  const downside = stop != null && latestClose != null && latestClose > 0 ? ((stop - latestClose) / latestClose) * 100 : null;

  return (
    // Gradient ring border (image 3)
    <div className="rounded-2xl bg-gradient-to-r from-emerald-500/40 via-sky-500/30 to-purple-500/40 p-px">
      <div className="rounded-2xl bg-slate-950/90 p-6">
        <div className="mb-5 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-emerald-400" />
          <h2 className="text-xl font-bold text-white">投資決策摘要</h2>
        </div>

        {/* Top metric row */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCell>
            <div className="mb-2 text-sm text-slate-400">綜合建議</div>
            <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 ${sig.border} ${sig.bg}`}>
              <SigIcon className={`h-5 w-5 ${sig.text}`} />
              <span className={`text-2xl font-bold ${sig.text}`}>{sig.label.split(' ')[0]}</span>
            </div>
            <div className="mt-2 text-xs text-slate-500">基於多維度分析結果</div>
          </MetricCell>

          <MetricCell>
            <div className="mb-2 flex items-center gap-1 text-sm text-slate-400">綜合評分 <Info className="h-3 w-3" /></div>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white">{score != null ? score.toFixed(0) : '--'}</span>
              <span className="text-sm text-slate-400">/100</span>
            </div>
            {score != null && (
              <span className={`mt-2 inline-block rounded-md border border-slate-700 px-2 py-0.5 text-xs font-medium ${tier.text}`}>{tier.label}</span>
            )}
          </MetricCell>

          <MetricCell>
            <div className="mb-2 flex items-center gap-1 text-sm text-slate-400">目標價 <Info className="h-3 w-3" /></div>
            <div className="text-3xl font-bold text-red-400">{target != null ? target.toLocaleString('en-US', { minimumFractionDigits: 0 }) : '--'}</div>
            {upside != null && (
              <div className={`mt-1 text-xs font-medium ${upside >= 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                {upside >= 0 ? '+' : ''}{upside.toFixed(1)}% 潛在{upside >= 0 ? '漲幅' : '跌幅'}
              </div>
            )}
          </MetricCell>

          <MetricCell>
            <div className="mb-2 flex items-center gap-1 text-sm text-slate-400">停損價 <Info className="h-3 w-3" /></div>
            <div className="text-3xl font-bold text-emerald-400">{stop != null ? stop.toLocaleString('en-US', { minimumFractionDigits: 0 }) : '--'}</div>
            {downside != null && (
              <div className="mt-1 text-xs font-medium text-emerald-400">{downside.toFixed(1)}% 風險空間</div>
            )}
            {report?.risk_level && (
              <span className="mt-2 inline-block rounded-md border border-red-500/40 px-2 py-0.5 text-xs font-medium text-red-300">風險等級 {report.risk_level}</span>
            )}
          </MetricCell>

          <MetricCell>
            <div className="mb-2 flex items-center gap-1 text-sm text-slate-400">AI 信心度 <Info className="h-3 w-3" /></div>
            <div className={`text-3xl font-bold ${confLbl.text}`}>{conf != null ? `${conf}%` : '--'}</div>
            {conf != null && (
              <>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-700">
                  <div className="h-full rounded-full bg-emerald-400" style={{ width: `${conf}%` }} />
                </div>
                <div className={`mt-1.5 text-xs ${confLbl.text}`}>{confLbl.label}</div>
              </>
            )}
          </MetricCell>
        </div>

        {/* Outlook rows */}
        {(report?.short_term_outlook || report?.medium_term_outlook || report?.long_term_outlook) && (
          <div className="mt-5 divide-y divide-white/10 rounded-xl border border-slate-800 bg-slate-900/30 px-5">
            {report?.short_term_outlook && <OutlookRow iconBg="bg-emerald-500/15" icon={<TrendingUp className="h-5 w-5 text-emerald-400" />} label="短線展望" timeframe="1-2 週" text={report.short_term_outlook} />}
            {report?.medium_term_outlook && <OutlookRow iconBg="bg-sky-500/15" icon={<Calendar className="h-5 w-5 text-sky-400" />} label="中線展望" timeframe="1-3 月" text={report.medium_term_outlook} />}
            {report?.long_term_outlook && <OutlookRow iconBg="bg-purple-500/15" icon={<Target className="h-5 w-5 text-purple-400" />} label="長線展望" timeframe="3-12 月" text={report.long_term_outlook} />}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 flex flex-col gap-2 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span className="flex items-center gap-1"><Info className="h-3.5 w-3.5" /> 本摘要由 AI 模型根據多維度數據分析產生，僅供參考，投資請謹慎評估風險。</span>
          <span className="flex items-center gap-2">
            {reportDate && <span>更新時間：{reportDate}</span>}
            <button onClick={onGenerate} disabled={generating} className="text-slate-400 transition-colors hover:text-emerald-400 disabled:opacity-50" title="重新產生分析">
              <RefreshCw className={`h-4 w-4 ${generating ? 'animate-spin' : ''}`} />
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ scores, scoresLoading, report, latestClose, generating, genError, onGenerate }: { scores: any; scoresLoading: boolean; report: any; latestClose: number | null; generating: boolean; genError: string | null; onGenerate: () => void }) {
  if (scoresLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64 rounded-xl bg-slate-800" />
          <Skeleton className="h-64 rounded-xl bg-slate-800" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl bg-slate-800" />
          ))}
        </div>
      </div>
    );
  }

  if (!scores) {
    return (
      <Card className="border-slate-800 bg-slate-900">
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <Sparkles className="h-10 w-10 text-emerald-400/70" />
          <div>
            <p className="text-white">尚無 AI 分析資料</p>
            <p className="mt-1 text-sm text-slate-400">點擊下方按鈕，立即產生這檔股票的五維度 AI 分析。</p>
          </div>
          <GenerateButton generating={generating} onGenerate={onGenerate} hasReport={false} />
          {genError && <p className="text-sm text-red-400">{genError}</p>}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-slate-400">資料日期：{scores.report_date ?? '--'}</p>
        <GenerateButton generating={generating} onGenerate={onGenerate} hasReport={!!report} />
      </div>
      {genError && <p className="text-sm text-red-400">{genError}</p>}

      <DecisionSummary scores={scores} report={report} latestClose={latestClose} reportDate={scores.report_date} generating={generating} onGenerate={onGenerate} />

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">綜合評分</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-center">
            <ScoreGauge score={scores.overall_score} label={signalDisplay(scores.overall_signal).label} size="lg" />
          </CardContent>
        </Card>
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">五維度雷達圖</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-center">
            <RadarChart dimensions={scores.dimensions} />
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {scores.dimensions.map((dim: DimensionScore) => {
          const Icon = DIMENSION_ICONS[dim.name] ?? BarChart3;
          return (
            <DimensionScoreCard key={dim.name} name={dim.name} score={dim.score} signal={dim.signal} icon={<Icon className="h-5 w-5" />} />
          );
        })}
      </div>
    </div>
  );
}

function NewsTab({ stockNews, newsLoading, sentimentSummary, socialPosts }: { stockNews: any; newsLoading: boolean; sentimentSummary: any; socialPosts: any }) {
  return (
    <div className="space-y-6">
      {sentimentSummary && (
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">消息面情緒總覽</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div><div className="text-xs text-slate-400">新聞情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.news_sentiment != null ? Number(sentimentSummary.news_sentiment).toFixed(2) : '--'}</div></div>
              <div><div className="text-xs text-slate-400">社群情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.social_sentiment != null ? Number(sentimentSummary.social_sentiment).toFixed(2) : '--'}</div></div>
              <div><div className="text-xs text-slate-400">綜合情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.combined_sentiment != null ? Number(sentimentSummary.combined_sentiment).toFixed(2) : '--'}</div></div>
              <div><div className="text-xs text-slate-400">提及次數</div><div className="text-lg font-semibold text-white">{sentimentSummary.mention_count}</div></div>
            </div>
          </CardContent>
        </Card>
      )}
      <div>
        <h3 className="mb-3 text-base font-semibold text-white">相關新聞</h3>
        {newsLoading ? (
          <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => (<Card key={i} className="border-slate-800 bg-slate-900"><CardContent className="space-y-2"><Skeleton className="h-4 w-3/4 bg-slate-700" /><Skeleton className="h-3 w-1/2 bg-slate-700" /></CardContent></Card>))}</div>
        ) : stockNews && stockNews.length > 0 ? (
          <div className="space-y-3">{stockNews.map((news: any) => (<NewsCard key={news.id} news={news} />))}</div>
        ) : (
          <p className="text-sm text-slate-500">暫無相關新聞</p>
        )}
      </div>
      {socialPosts && socialPosts.length > 0 && (
        <div>
          <h3 className="mb-3 text-base font-semibold text-white">社群討論 (PTT)</h3>
          <div className="space-y-2">
            {socialPosts.map((post: any) => (
              <Card key={post.id} className="cursor-pointer border-slate-800 bg-slate-900 transition-colors hover:border-slate-700" onClick={() => { if (post.url) window.open(post.url, '_blank', 'noopener,noreferrer'); }}>
                <CardContent className="flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white">{post.title}</p>
                    <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
                      {post.author && <span>{post.author}</span>}
                      {post.posted_at && <span>{new Date(post.posted_at).toLocaleDateString('zh-TW')}</span>}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-emerald-400">推 {post.push_count}</span>
                    <span className="text-xs text-red-400">噓 {post.boo_count}</span>
                    <SentimentBadge sentiment={post.sentiment} score={post.sentiment_score} />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TechnicalTab({ prices, pricesLoading, technicalData, technicalLoading }: { prices: any; pricesLoading: boolean; technicalData: any; technicalLoading: boolean }) {
  if (pricesLoading || technicalLoading) {
    return (<div className="space-y-4"><Skeleton className="h-[400px] rounded-xl bg-slate-800" /><Skeleton className="h-[140px] rounded-xl bg-slate-800" /><Skeleton className="h-48 rounded-xl bg-slate-800" /></div>);
  }
  const hasPrices = prices && Array.isArray(prices) && prices.length > 0;
  const hasIndicators = technicalData?.indicators;
  const hasSignals = technicalData?.signals && Array.isArray(technicalData.signals);
  if (!hasPrices && !hasIndicators && !hasSignals) {
    return (<Card className="border-slate-800 bg-slate-900"><CardContent className="py-10 text-center text-slate-400">尚無技術面資料</CardContent></Card>);
  }
  const indicatorDates = hasPrices
    ? [...prices].sort((a: any, b: any) => a.date.localeCompare(b.date)).map((p: any) => p.date)
    : undefined;
  return (
    <div className="space-y-6">
      {hasPrices && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">股價走勢圖</CardTitle></CardHeader><CardContent><PriceChart prices={prices} height={400} /></CardContent></Card>)}
      {hasIndicators && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">技術指標</CardTitle></CardHeader><CardContent><IndicatorPanel indicators={technicalData.indicators} dates={indicatorDates} /></CardContent></Card>)}
      {(hasSignals || technicalData?.score != null) && (<TechnicalSummary signals={technicalData?.signals ?? []} score={technicalData?.score ?? 0} summary={technicalData?.summary ?? ''} />)}
    </div>
  );
}

function FundamentalTab({ fundamentalData, fundamentalLoading, statements, statementsLoading }: { fundamentalData: any; fundamentalLoading: boolean; statements: any; statementsLoading: boolean }) {
  if (fundamentalLoading || statementsLoading) {
    return (<div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => (<Skeleton key={i} className="h-24 rounded-xl bg-slate-800" />))}</div><Skeleton className="h-64 rounded-xl bg-slate-800" /></div>);
  }
  const hasFundamentals = fundamentalData && (fundamentalData.fundamentals || fundamentalData.pe_ratio != null);
  const fundamentals = fundamentalData?.fundamentals ?? fundamentalData ?? {};
  const industryAvg = fundamentalData?.industry_avg ?? {};
  // The /financials endpoint returns { statements: [{year, quarter, ...}] }.
  // Normalise to the shape the chart/table components expect (report_year/report_quarter).
  const rawStatements = Array.isArray(statements)
    ? statements
    : (statements?.statements ?? fundamentalData?.statements ?? []);
  const statementsArray = rawStatements.map((s: any) => ({
    ...s,
    report_year: s.report_year ?? s.year,
    report_quarter: s.report_quarter ?? s.quarter,
  }));
  const hasStatements = statementsArray.length > 0;
  if (!hasFundamentals && !hasStatements) {
    return (<Card className="border-slate-800 bg-slate-900"><CardContent className="py-10 text-center text-slate-400">尚無基本面資料</CardContent></Card>);
  }
  return (
    <div className="space-y-6">
      {hasFundamentals && <ValuationMetrics fundamentals={fundamentals} industry_avg={industryAvg} />}
      {hasFundamentals && <FinancialTable fundamentals={fundamentals} statements={statementsArray} />}
      {statementsArray.length > 0 && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">營收趨勢</CardTitle></CardHeader><CardContent><RevenueChart statements={statementsArray} /></CardContent></Card>)}
    </div>
  );
}

function InstitutionalTab({ institutionalData, institutionalLoading, marginData, marginLoading, chipSummary, chipSummaryLoading }: { institutionalData: any; institutionalLoading: boolean; marginData: any; marginLoading: boolean; chipSummary: any; chipSummaryLoading: boolean }) {
  if (institutionalLoading || marginLoading || chipSummaryLoading) {
    return (<div className="space-y-4"><Skeleton className="h-72 rounded-xl bg-slate-800" /><Skeleton className="h-64 rounded-xl bg-slate-800" /></div>);
  }
  const institutionalArray = (institutionalData && Array.isArray(institutionalData)) ? institutionalData : (institutionalData?.data ?? []);
  const marginArray = Array.isArray(marginData) ? marginData : (marginData?.data ?? []);
  const hasChipSummary = chipSummary && Object.keys(chipSummary).length > 0;
  if (institutionalArray.length === 0 && marginArray.length === 0 && !hasChipSummary) {
    return (<Card className="border-slate-800 bg-slate-900"><CardContent className="py-10 text-center text-slate-400">尚無籌碼面資料</CardContent></Card>);
  }
  return (
    <div className="space-y-6">
      {institutionalArray.length > 0 && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">三大法人買賣超</CardTitle></CardHeader><CardContent><InstitutionalChart data={institutionalArray} /></CardContent></Card>)}
      {marginArray.length > 0 && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">融資融券</CardTitle></CardHeader><CardContent><MarginChart data={marginArray} /></CardContent></Card>)}
      {hasChipSummary && <ChipSummary analysis={chipSummary} />}
    </div>
  );
}

function ReportTab({ report, reportLoading, generating, genError, onGenerate }: { report: any; reportLoading: boolean; generating: boolean; genError: string | null; onGenerate: () => void }) {
  if (reportLoading) {
    return (<div className="space-y-4"><Skeleton className="h-8 w-48 bg-slate-800" /><Skeleton className="h-64 w-full rounded-xl bg-slate-800" /></div>);
  }
  if (!report) {
    return (
      <Card className="border-slate-800 bg-slate-900">
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <Sparkles className="h-10 w-10 text-emerald-400/70" />
          <p className="text-slate-400">尚無分析報告，點擊下方按鈕立即產生。</p>
          <GenerateButton generating={generating} onGenerate={onGenerate} hasReport={false} />
          {genError && <p className="text-sm text-red-400">{genError}</p>}
        </CardContent>
      </Card>
    );
  }
  const conf = confidencePct(report.confidence);
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <GenerateButton generating={generating} onGenerate={onGenerate} hasReport={true} />
      </div>
      {genError && <p className="text-right text-sm text-red-400">{genError}</p>}
      <Card className="border-slate-800 bg-slate-900">
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {report.report_date && (<div className="flex items-center gap-2"><Calendar className="h-4 w-4 text-slate-400" /><div><div className="text-xs text-slate-400">報告日期</div><div className="text-sm font-medium text-white">{report.report_date}</div></div></div>)}
            {report.ai_provider && (<div><div className="text-xs text-slate-400">AI 模型</div><div className="text-sm font-medium text-white">{report.ai_provider}</div></div>)}
            {report.risk_level && (<div className="flex items-center gap-2"><Shield className="h-4 w-4 text-slate-400" /><div><div className="text-xs text-slate-400">風險等級</div><div className="text-sm font-medium text-white">{report.risk_level}</div></div></div>)}
            {conf != null && (<div><div className="text-xs text-slate-400">信心度</div><div className="text-sm font-medium text-white">{conf}%</div></div>)}
          </div>
        </CardContent>
      </Card>
      {(report.target_price != null || report.stop_loss_price != null) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {report.target_price != null && (<Card className="border-red-500/30 bg-red-500/5"><CardContent className="flex items-center gap-3 py-4"><Target className="h-6 w-6 text-red-400" /><div><div className="text-xs text-slate-400">目標價</div><div className="text-xl font-bold text-red-400">{Number(report.target_price).toFixed(2)}</div></div></CardContent></Card>)}
          {report.stop_loss_price != null && (<Card className="border-emerald-500/30 bg-emerald-500/5"><CardContent className="flex items-center gap-3 py-4"><AlertTriangle className="h-6 w-6 text-emerald-400" /><div><div className="text-xs text-slate-400">停損價</div><div className="text-xl font-bold text-emerald-400">{Number(report.stop_loss_price).toFixed(2)}</div></div></CardContent></Card>)}
        </div>
      )}
      {report.ai_report_markdown && (
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">AI 完整分析報告</CardTitle></CardHeader>
          <CardContent>
            <div className="prose prose-invert max-w-none prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-ul:text-slate-300 prose-ol:text-slate-300 prose-li:text-slate-300">
              <ReactMarkdown>{report.ai_report_markdown}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
