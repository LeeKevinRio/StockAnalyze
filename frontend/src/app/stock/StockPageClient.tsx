'use client';

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

interface StockPageClientProps {
  stockId: string;
}

export default function StockPageClient({ stockId }: StockPageClientProps) {
  // Core data
  const { data: detail, isLoading: detailLoading, error: detailError } = useStockDetail(stockId);
  const { data: scores, isLoading: scoresLoading } = useAnalysisScores(stockId);
  const { data: report, isLoading: reportLoading } = useAnalysisReport(stockId);
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
      <div className="min-h-screen bg-slate-950 pt-14">
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
  const priceChange = detail?.price_change ?? 0;
  const priceChangePercent = detail?.price_change_percent ?? 0;
  const isPositive = priceChange >= 0;

  return (
    <div className="min-h-screen bg-slate-950 pt-14">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-slate-400 transition-colors hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </Link>

        <header className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-1 flex items-center gap-3">
                <h1 className="text-2xl font-bold text-white md:text-3xl">
                  {stock?.name ?? stockId}
                </h1>
                <span className="font-mono text-lg text-slate-400">
                  {stock?.stock_id ?? stockId}
                </span>
              </div>
              {stock?.industry && (
                <span className="text-sm text-slate-500">{stock.industry}</span>
              )}
            </div>
            <div className="flex items-end gap-4">
              {latestPrice?.close != null && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-white md:text-3xl">
                    {latestPrice.close.toFixed(2)}
                  </div>
                  <div className={`text-sm font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isPositive ? '+' : ''}{priceChange.toFixed(2)} ({isPositive ? '+' : ''}{priceChangePercent.toFixed(2)}%)
                  </div>
                </div>
              )}
              {scores && (
                <SentimentBadge
                  sentiment={scores.overall_signal}
                  score={scores.overall_score ? scores.overall_score / 100 : null}
                />
              )}
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
            <OverviewTab scores={scores} scoresLoading={scoresLoading} report={report} />
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
            <ReportTab report={report} reportLoading={reportLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

/* ---- Tab Components ---- */

function OverviewTab({ scores, scoresLoading, report }: { scores: any; scoresLoading: boolean; report: any }) {
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
        <CardContent className="py-10 text-center text-slate-400">暫無分析資料</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">綜合評分</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-center">
            <ScoreGauge score={scores.overall_score} label={scores.overall_signal === 'bullish' ? '看多' : scores.overall_signal === 'bearish' ? '看空' : '中性'} size="lg" />
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
      {report?.short_term_outlook && (
        <Card className="border-slate-800 bg-slate-900">
          <CardHeader><CardTitle className="text-white">AI 短期展望</CardTitle></CardHeader>
          <CardContent><p className="leading-relaxed text-slate-300">{report.short_term_outlook}</p></CardContent>
        </Card>
      )}
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
              <div><div className="text-xs text-slate-400">新聞情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.news_sentiment?.toFixed(2) ?? '--'}</div></div>
              <div><div className="text-xs text-slate-400">社群情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.social_sentiment?.toFixed(2) ?? '--'}</div></div>
              <div><div className="text-xs text-slate-400">綜合情緒</div><div className="text-lg font-semibold text-white">{sentimentSummary.combined_sentiment?.toFixed(2) ?? '--'}</div></div>
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
  return (
    <div className="space-y-6">
      {hasPrices && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">股價走勢圖</CardTitle></CardHeader><CardContent><PriceChart prices={prices} height={400} /></CardContent></Card>)}
      {hasIndicators && (<Card className="border-slate-800 bg-slate-900"><CardHeader><CardTitle className="text-white">技術指標</CardTitle></CardHeader><CardContent><IndicatorPanel indicators={technicalData.indicators} /></CardContent></Card>)}
      {(hasSignals || technicalData?.score != null) && (<TechnicalSummary signals={technicalData?.signals ?? []} score={technicalData?.score ?? 0} summary={technicalData?.summary ?? ''} />)}
    </div>
  );
}

function FundamentalTab({ fundamentalData, fundamentalLoading, statements, statementsLoading }: { fundamentalData: any; fundamentalLoading: boolean; statements: any; statementsLoading: boolean }) {
  if (fundamentalLoading || statementsLoading) {
    return (<div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => (<Skeleton key={i} className="h-24 rounded-xl bg-slate-800" />))}</div><Skeleton className="h-64 rounded-xl bg-slate-800" /></div>);
  }
  const hasFundamentals = fundamentalData && (fundamentalData.fundamentals || fundamentalData.pe_ratio != null);
  const hasStatements = statements && Array.isArray(statements) && statements.length > 0;
  const fundamentals = fundamentalData?.fundamentals ?? fundamentalData ?? {};
  const industryAvg = fundamentalData?.industry_avg ?? {};
  const statementsArray = hasStatements ? statements : (fundamentalData?.statements ?? []);
  if (!hasFundamentals && !hasStatements && statementsArray.length === 0) {
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

function ReportTab({ report, reportLoading }: { report: any; reportLoading: boolean }) {
  if (reportLoading) {
    return (<div className="space-y-4"><Skeleton className="h-8 w-48 bg-slate-800" /><Skeleton className="h-64 w-full rounded-xl bg-slate-800" /></div>);
  }
  if (!report) {
    return (<Card className="border-slate-800 bg-slate-900"><CardContent className="py-10 text-center text-slate-400">暫無分析報告</CardContent></Card>);
  }
  return (
    <div className="space-y-6">
      <Card className="border-slate-800 bg-slate-900">
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {report.report_date && (<div className="flex items-center gap-2"><Calendar className="h-4 w-4 text-slate-400" /><div><div className="text-xs text-slate-400">報告日期</div><div className="text-sm font-medium text-white">{report.report_date}</div></div></div>)}
            {report.ai_provider && (<div><div className="text-xs text-slate-400">AI 模型</div><div className="text-sm font-medium text-white">{report.ai_provider}</div></div>)}
            {report.risk_level && (<div className="flex items-center gap-2"><Shield className="h-4 w-4 text-slate-400" /><div><div className="text-xs text-slate-400">風險等級</div><div className="text-sm font-medium text-white">{report.risk_level}</div></div></div>)}
            {report.confidence != null && (<div><div className="text-xs text-slate-400">信心度</div><div className="text-sm font-medium text-white">{report.confidence}%</div></div>)}
          </div>
        </CardContent>
      </Card>
      {(report.target_price != null || report.stop_loss_price != null) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {report.target_price != null && (<Card className="border-emerald-500/30 bg-emerald-500/5"><CardContent className="flex items-center gap-3 py-4"><Target className="h-6 w-6 text-emerald-400" /><div><div className="text-xs text-slate-400">目標價</div><div className="text-xl font-bold text-emerald-400">{report.target_price.toFixed(2)}</div></div></CardContent></Card>)}
          {report.stop_loss_price != null && (<Card className="border-red-500/30 bg-red-500/5"><CardContent className="flex items-center gap-3 py-4"><AlertTriangle className="h-6 w-6 text-red-400" /><div><div className="text-xs text-slate-400">停損價</div><div className="text-xl font-bold text-red-400">{report.stop_loss_price.toFixed(2)}</div></div></CardContent></Card>)}
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
