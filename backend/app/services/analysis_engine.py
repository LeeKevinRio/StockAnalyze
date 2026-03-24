"""Multi-dimension stock analysis engine — the brain of the platform.

Orchestrates all five analysis dimensions (消息面, 基本面, 技術面, 籌碼面, 總經面),
applies regime-aware dynamic weighting, and produces a comprehensive analysis
result that feeds into the AI report generator.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock, StockPrice

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """Complete multi-dimension analysis output."""

    stock_id: str = ""
    stock_name: str = ""
    scores: dict = field(default_factory=dict)
    # {news: float, fundamental: float, technical: float, institutional: float, macro: float}
    overall_score: float = 0.0
    overall_signal: str = "neutral"
    confidence: float = 0.5
    regime: str = "sideways"  # bull, bear, sideways
    weights_used: dict = field(default_factory=dict)
    dimension_details: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AnalysisEngine:
    """Multi-dimension stock analysis engine.

    Orchestrates: 消息面, 基本面, 技術面, 籌碼面, 總經面
    Produces weighted scores and triggers AI report generation.
    """

    WEIGHTS_BULL = {
        "news": 0.30,
        "fundamental": 0.15,
        "technical": 0.20,
        "institutional": 0.20,
        "macro": 0.15,
    }
    WEIGHTS_BEAR = {
        "news": 0.32,
        "fundamental": 0.10,
        "technical": 0.15,
        "institutional": 0.28,
        "macro": 0.15,
    }
    WEIGHTS_SIDEWAYS = {
        "news": 0.27,
        "fundamental": 0.13,
        "technical": 0.30,
        "institutional": 0.18,
        "macro": 0.12,
    }

    async def analyze(self, stock_id: str, db: AsyncSession) -> AnalysisResult:
        """Run full multi-dimension analysis for a stock.

        Steps:
        1. Fetch all data in parallel (asyncio.gather)
        2. Score each dimension
        3. Detect market regime
        4. Apply regime-aware dynamic weighting
        5. Generate overall signal
        6. Return structured result

        Args:
            stock_id: Taiwan stock ID (e.g. ``"2330"``).
            db: Async database session.

        Returns:
            AnalysisResult with all dimensions scored and weighted.
        """
        result = AnalysisResult(stock_id=stock_id)

        # Fetch stock info
        stock = await self._get_stock(stock_id, db)
        if stock:
            result.stock_name = stock.name
        else:
            result.stock_name = stock_id

        # Collect all data in parallel
        collected = await self._collect_data(stock_id, db)
        result.raw_data = collected

        # Score each dimension
        scores = {}
        details = {}

        # 1) News / Sentiment dimension (消息面)
        news_score, news_detail = self._score_news(collected)
        scores["news"] = news_score
        details["news"] = news_detail

        # 2) Fundamental dimension (基本面)
        fund_score, fund_detail = self._score_fundamental(collected)
        scores["fundamental"] = fund_score
        details["fundamental"] = fund_detail

        # 3) Technical dimension (技術面)
        tech_score, tech_detail = self._score_technical(collected)
        scores["technical"] = tech_score
        details["technical"] = tech_detail

        # 4) Institutional / Chip dimension (籌碼面)
        inst_score, inst_detail = self._score_institutional(collected)
        scores["institutional"] = inst_score
        details["institutional"] = inst_detail

        # 5) Macro dimension (總經面)
        macro_score, macro_detail = self._score_macro(collected)
        scores["macro"] = macro_score
        details["macro"] = macro_detail

        result.scores = scores
        result.dimension_details = details

        # Detect market regime from prices
        prices = collected.get("prices", [])
        result.regime = self._detect_market_regime(prices)

        # Apply regime-aware weighting
        result.weights_used = self._get_weights(result.regime)
        result.overall_score = self._apply_weights(scores, result.regime)

        # Determine signal and confidence
        result.overall_signal = self._determine_signal(result.overall_score)
        result.confidence = self._calculate_confidence(scores)

        logger.info(
            "Analysis complete for %s: score=%.1f signal=%s confidence=%.2f regime=%s",
            stock_id,
            result.overall_score,
            result.overall_signal,
            result.confidence,
            result.regime,
        )

        return result

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    async def _collect_data(self, stock_id: str, db: AsyncSession) -> dict:
        """Parallel data collection from all services.

        Uses asyncio.gather to fetch data from all five dimensions
        concurrently. Each fetch is wrapped in error handling so that
        one failure does not prevent the others from completing.

        Args:
            stock_id: Taiwan stock ID.
            db: Async database session.

        Returns:
            Dict keyed by data category with all collected data.
        """
        # Prepare all async tasks
        tasks = {
            "prices": self._fetch_prices(stock_id, db, days=120),
            "news": self._fetch_news(stock_id, db),
            "sentiment": self._fetch_sentiment(stock_id, db),
            "fundamentals": self._fetch_fundamentals(stock_id, db),
            "statements": self._fetch_statements(stock_id, db),
            "dividends": self._fetch_dividends(stock_id, db),
            "peers": self._fetch_peers(stock_id, db),
            "institutional": self._fetch_institutional(stock_id, db),
            "margin": self._fetch_margin(stock_id, db),
            "macro": self._fetch_macro(db),
        }

        results = {}
        # Run all tasks concurrently
        gathered = await asyncio.gather(
            *[self._safe_fetch(name, coro) for name, coro in tasks.items()],
            return_exceptions=False,
        )

        for (name, _), data in zip(tasks.items(), gathered):
            results[name] = data

        return results

    @staticmethod
    async def _safe_fetch(name: str, coro) -> any:
        """Execute a coroutine with error handling.

        Returns the result on success, empty data on failure.
        """
        try:
            return await coro
        except Exception as exc:
            logger.warning("Failed to fetch %s data: %s", name, exc)
            return None

    # ------------------------------------------------------------------
    # Individual data fetch methods
    # ------------------------------------------------------------------

    async def _get_stock(self, stock_id: str, db: AsyncSession) -> Optional[Stock]:
        """Get stock info."""
        stmt = select(Stock).where(Stock.stock_id == stock_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_prices(
        self, stock_id: str, db: AsyncSession, days: int = 120
    ) -> list[dict]:
        """Fetch recent price data, sorted ascending."""
        stmt = (
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .limit(days)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        # Return in ascending order for technical analysis
        prices = []
        for row in reversed(rows):
            prices.append({
                "date": row.date.isoformat() if row.date else "",
                "open": float(row.open) if row.open else None,
                "high": float(row.high) if row.high else None,
                "low": float(row.low) if row.low else None,
                "close": float(row.close) if row.close else None,
                "volume": int(row.volume) if row.volume else None,
            })
        return prices

    async def _fetch_news(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch recent news articles."""
        from app.services.news_service import get_stock_news
        news = await get_stock_news(stock_id, db, limit=20)
        return [
            {
                "title": n.title,
                "sentiment": n.sentiment,
                "sentiment_score": float(n.sentiment_score) if n.sentiment_score else None,
                "source": n.source,
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "impact_level": n.impact_level,
            }
            for n in news
        ]

    async def _fetch_sentiment(self, stock_id: str, db: AsyncSession) -> dict:
        """Fetch sentiment summary."""
        from app.services.sentiment_service import get_stock_sentiment_summary
        return await get_stock_sentiment_summary(stock_id, db)

    async def _fetch_fundamentals(self, stock_id: str, db: AsyncSession) -> dict:
        """Fetch fundamental metrics."""
        from app.services.fundamental_service import fundamental_service
        return await fundamental_service.get_fundamentals(stock_id, db)

    async def _fetch_statements(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch financial statements."""
        from app.services.fundamental_service import fundamental_service
        return await fundamental_service.get_financial_statements(stock_id, db, quarters=8)

    async def _fetch_dividends(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch dividend history."""
        from app.services.fundamental_service import fundamental_service
        return await fundamental_service.get_dividends(stock_id, db, years=5)

    async def _fetch_peers(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch peer stocks."""
        from app.services.fundamental_service import fundamental_service
        return await fundamental_service.get_peer_stocks(stock_id, db)

    async def _fetch_institutional(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch institutional trading data."""
        from app.services.institutional_service import institutional_service
        return await institutional_service.get_institutional_data(stock_id, db, days=30)

    async def _fetch_margin(self, stock_id: str, db: AsyncSession) -> list:
        """Fetch margin trading data."""
        from app.services.institutional_service import institutional_service
        return await institutional_service.get_margin_data(stock_id, db, days=30)

    async def _fetch_macro(self, db: AsyncSession) -> dict:
        """Fetch macro indicators."""
        from app.services.macro_service import macro_service
        return await macro_service.get_macro_indicators(db)

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _score_news(self, collected: dict) -> tuple[float, dict]:
        """Score the news / sentiment dimension.

        Uses news articles sentiment scores and aggregated sentiment summary.

        Returns:
            Tuple of (score, detail_dict).
        """
        news = collected.get("news") or []
        sentiment = collected.get("sentiment") or {}

        if not news and not sentiment.get("combined_score"):
            return 0.0, {"summary": "無消息面資料", "available": False}

        score = 0.0

        # News article sentiment
        if news:
            positive_count = 0
            negative_count = 0
            total_sentiment = 0.0
            high_impact_sentiment = 0.0
            high_impact_count = 0

            for article in news:
                sent_score = article.get("sentiment_score")
                if sent_score is not None:
                    total_sentiment += sent_score
                    if article.get("impact_level") == "high":
                        high_impact_sentiment += sent_score
                        high_impact_count += 1
                sentiment_label = article.get("sentiment", "")
                if sentiment_label == "positive":
                    positive_count += 1
                elif sentiment_label == "negative":
                    negative_count += 1

            # Average sentiment score -> scale to -100..+100
            if len(news) > 0:
                avg_sentiment = total_sentiment / len(news)
                score += avg_sentiment * 60  # Scale from [-1,1] to [-60,+60]

            # High-impact news bonus/penalty
            if high_impact_count > 0:
                avg_high = high_impact_sentiment / high_impact_count
                score += avg_high * 20

            # Volume of news (many articles = higher conviction)
            if len(news) >= 10:
                score *= 1.1  # Slightly boost conviction

        # Combined sentiment from social + news
        combined = sentiment.get("combined_score")
        if combined is not None:
            score += combined * 20  # Additional signal from social

        # Heat level bonus
        heat = sentiment.get("heat_level", "cold")
        if heat == "hot":
            # Hot topic amplifies the existing signal direction
            score *= 1.15

        score = max(-100.0, min(100.0, score))

        detail = {
            "available": True,
            "news_count": len(news),
            "combined_sentiment": combined,
            "heat_level": heat,
            "summary": self._news_summary(score, len(news), heat),
        }

        return score, detail

    def _score_fundamental(self, collected: dict) -> tuple[float, dict]:
        """Score the fundamental dimension.

        Returns:
            Tuple of (score, detail_dict).
        """
        fundamentals = collected.get("fundamentals") or {}
        statements = collected.get("statements") or []
        dividends = collected.get("dividends") or []
        peers = collected.get("peers") or []

        if not fundamentals:
            return 0.0, {"summary": "無基本面資料", "available": False}

        from app.services.fundamental_service import fundamental_service

        analysis = fundamental_service.analyze(fundamentals, statements, dividends, peers)
        score = fundamental_service.calculate_score(analysis)
        summary = fundamental_service.generate_summary(score, analysis)

        detail = {
            "available": True,
            "pe_ratio": analysis.pe_ratio,
            "eps": analysis.eps,
            "roe": analysis.roe,
            "dividend_yield": analysis.dividend_yield,
            "eps_growth_yoy": analysis.eps_growth_yoy,
            "revenue_growth_yoy": analysis.revenue_growth_yoy,
            "industry_pe_avg": analysis.industry_pe_avg,
            "valuation_assessment": analysis.valuation_assessment,
            "growth_assessment": analysis.growth_assessment,
            "profitability_assessment": analysis.profitability_assessment,
            "summary": summary,
        }

        return score, detail

    def _score_technical(self, collected: dict) -> tuple[float, dict]:
        """Score the technical dimension.

        Returns:
            Tuple of (score, detail_dict).
        """
        prices = collected.get("prices") or []

        if not prices or len(prices) < 5:
            return 0.0, {"summary": "無足夠價格資料", "available": False}

        from app.services.technical_service import technical_service

        tech_result = technical_service.calculate_all(prices)

        detail = {
            "available": True,
            "indicators": tech_result.indicators,
            "signals": tech_result.signals,
            "score": tech_result.score,
            "summary": tech_result.summary,
        }

        return tech_result.score, detail

    def _score_institutional(self, collected: dict) -> tuple[float, dict]:
        """Score the institutional / chip dimension.

        Returns:
            Tuple of (score, detail_dict).
        """
        institutional_data = collected.get("institutional") or []
        margin_data = collected.get("margin") or []

        if not institutional_data:
            return 0.0, {"summary": "無籌碼面資料", "available": False}

        from app.services.institutional_service import institutional_service

        inst_result = institutional_service.analyze_institutional(institutional_data)
        margin_result = institutional_service.analyze_margin(margin_data)
        score = institutional_service.calculate_score(inst_result, margin_result)

        detail = {
            "available": True,
            "foreign_trend": inst_result.foreign_trend,
            "trust_trend": inst_result.trust_trend,
            "dealer_trend": inst_result.dealer_trend,
            "foreign_consecutive_days": inst_result.foreign_consecutive_days,
            "cumulative_foreign_20d": inst_result.cumulative_foreign_20d,
            "cumulative_trust_20d": inst_result.cumulative_trust_20d,
            "margin_trend": margin_result.margin_trend,
            "short_trend": margin_result.short_trend,
            "squeeze_potential": margin_result.squeeze_potential,
            "summary": f"外資{'買超' if inst_result.foreign_trend == 'buying' else '賣超' if inst_result.foreign_trend == 'selling' else '中性'}，"
                       f"投信{'買超' if inst_result.trust_trend == 'buying' else '賣超' if inst_result.trust_trend == 'selling' else '中性'}。",
        }

        return score, detail

    def _score_macro(self, collected: dict) -> tuple[float, dict]:
        """Score the macro dimension.

        Returns:
            Tuple of (score, detail_dict).
        """
        macro_indicators = collected.get("macro") or {}

        if not macro_indicators:
            return 0.0, {"summary": "無總經面資料", "available": False}

        from app.services.macro_service import macro_service

        analysis = macro_service.analyze(macro_indicators)
        score = macro_service.calculate_score(analysis)
        summary = macro_service.generate_summary(score, analysis)

        detail = {
            "available": True,
            "rate_cycle": analysis.rate_cycle,
            "business_cycle": analysis.business_cycle,
            "taiex_trend": analysis.taiex_trend,
            "vix_level": analysis.vix_level,
            "summary": summary,
        }

        return score, detail

    # ------------------------------------------------------------------
    # Market regime detection
    # ------------------------------------------------------------------

    def _detect_market_regime(self, prices: list[dict]) -> str:
        """Detect current market regime: 'bull', 'bear', 'sideways'.

        Logic:
        - If price > MA20 > MA60 and MA20 slope positive: bull
        - If price < MA20 < MA60 and MA20 slope negative: bear
        - Otherwise: sideways

        Args:
            prices: List of price dicts sorted ascending.

        Returns:
            One of 'bull', 'bear', 'sideways'.
        """
        closes = [p["close"] for p in prices if p.get("close") is not None]

        if len(closes) < 60:
            # Not enough data for full regime detection
            if len(closes) < 20:
                return "sideways"

            # Use shorter-term signals
            ma20 = sum(closes[-20:]) / 20
            current = closes[-1]

            if current > ma20 * 1.03:
                return "bull"
            elif current < ma20 * 0.97:
                return "bear"
            return "sideways"

        current = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60

        # MA20 slope: compare current MA20 vs 5 days ago
        ma20_5d_ago = sum(closes[-25:-5]) / 20 if len(closes) >= 25 else ma20

        ma20_slope_positive = ma20 > ma20_5d_ago

        if current > ma20 > ma60 and ma20_slope_positive:
            return "bull"
        elif current < ma20 < ma60 and not ma20_slope_positive:
            return "bear"
        return "sideways"

    # ------------------------------------------------------------------
    # Weighting and scoring
    # ------------------------------------------------------------------

    def _get_weights(self, regime: str) -> dict:
        """Get the weight set for the given regime."""
        if regime == "bull":
            return self.WEIGHTS_BULL.copy()
        elif regime == "bear":
            return self.WEIGHTS_BEAR.copy()
        return self.WEIGHTS_SIDEWAYS.copy()

    def _apply_weights(self, scores: dict, regime: str) -> float:
        """Apply regime-aware dynamic weighting to dimension scores.

        Args:
            scores: Dict of dimension scores {name: float}.
            regime: Current market regime.

        Returns:
            Weighted overall score clamped to [-100, +100].
        """
        weights = self._get_weights(regime)

        total = 0.0
        weight_sum = 0.0

        for dim, weight in weights.items():
            dim_score = scores.get(dim, 0.0)
            total += dim_score * weight
            weight_sum += weight

        # Normalize in case weights don't sum to 1.0
        if weight_sum > 0:
            overall = total / weight_sum
        else:
            overall = 0.0

        return max(-100.0, min(100.0, overall))

    def _determine_signal(self, overall_score: float) -> str:
        """Convert overall score to signal.

        Args:
            overall_score: Combined weighted score.

        Returns:
            One of: strong_buy, buy, neutral, sell, strong_sell.
        """
        if overall_score >= 60:
            return "strong_buy"
        elif overall_score >= 20:
            return "buy"
        elif overall_score >= -20:
            return "neutral"
        elif overall_score >= -60:
            return "sell"
        return "strong_sell"

    def _calculate_confidence(self, scores: dict) -> float:
        """Calculate confidence based on dimension agreement.

        Higher confidence when dimensions agree on direction, lower when
        they contradict each other. Also considers data availability.

        Args:
            scores: Dict of dimension scores.

        Returns:
            Confidence value between 0.0 and 1.0.
        """
        available_scores = [v for v in scores.values() if v != 0.0]

        if not available_scores:
            return 0.3  # Low confidence with no data

        # Count how many dimensions agree on direction
        positive = sum(1 for s in available_scores if s > 10)
        negative = sum(1 for s in available_scores if s < -10)
        total = len(available_scores)

        # Agreement ratio: max of positive or negative fraction
        if total == 0:
            return 0.3

        agreement = max(positive, negative) / total

        # Base confidence from agreement
        confidence = 0.3 + agreement * 0.5

        # Bonus for data completeness
        all_dims = ["news", "fundamental", "technical", "institutional", "macro"]
        available_dims = sum(1 for d in all_dims if scores.get(d, 0.0) != 0.0)
        completeness = available_dims / len(all_dims)
        confidence += completeness * 0.2

        # Bonus for strong signal consistency
        if positive >= 4 or negative >= 4:
            confidence += 0.05

        return min(1.0, max(0.0, round(confidence, 2)))

    # ------------------------------------------------------------------
    # Save report
    # ------------------------------------------------------------------

    async def save_report(
        self,
        stock_id: str,
        result: AnalysisResult,
        ai_report: str,
        ai_provider: str,
        db: AsyncSession,
        *,
        risk_level: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        short_term_outlook: Optional[str] = None,
        medium_term_outlook: Optional[str] = None,
        long_term_outlook: Optional[str] = None,
    ) -> None:
        """Save analysis results to analysis_reports table.

        Creates or updates a report for the given stock and today's date.

        Args:
            stock_id: Taiwan stock ID.
            result: The analysis result.
            ai_report: The generated AI report markdown.
            ai_provider: Name of the LLM provider used.
            db: Async database session.
            risk_level: Risk level (HIGH/MEDIUM/LOW).
            target_price: Target price from report.
            stop_loss_price: Stop loss price from report.
            short_term_outlook: Short term outlook text.
            medium_term_outlook: Medium term outlook text.
            long_term_outlook: Long term outlook text.
        """
        from app.models.analysis import AnalysisReport

        today = date.today()

        # Check for existing report today
        stmt = select(AnalysisReport).where(
            AnalysisReport.stock_id == stock_id,
            AnalysisReport.report_date == today,
        )
        existing_result = await db.execute(stmt)
        report = existing_result.scalar_one_or_none()

        if report is None:
            report = AnalysisReport(
                stock_id=stock_id,
                report_date=today,
            )
            db.add(report)

        # Update fields
        report.overall_score = Decimal(str(round(result.overall_score, 1)))
        report.overall_signal = result.overall_signal
        report.confidence = Decimal(str(round(result.confidence, 2)))

        report.news_score = Decimal(str(round(result.scores.get("news", 0), 1)))
        report.fundamental_score = Decimal(str(round(result.scores.get("fundamental", 0), 1)))
        report.technical_score = Decimal(str(round(result.scores.get("technical", 0), 1)))
        report.institutional_score = Decimal(str(round(result.scores.get("institutional", 0), 1)))
        report.macro_score = Decimal(str(round(result.scores.get("macro", 0), 1)))

        report.dimension_details = result.dimension_details
        report.ai_report_markdown = ai_report
        report.ai_provider = ai_provider

        report.risk_level = risk_level
        report.short_term_outlook = short_term_outlook
        report.medium_term_outlook = medium_term_outlook
        report.long_term_outlook = long_term_outlook

        if target_price is not None:
            report.target_price = Decimal(str(round(target_price, 2)))
        if stop_loss_price is not None:
            report.stop_loss_price = Decimal(str(round(stop_loss_price, 2)))

        await db.flush()

        logger.info(
            "Saved analysis report for %s: score=%.1f signal=%s",
            stock_id,
            result.overall_score,
            result.overall_signal,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _news_summary(score: float, count: int, heat: str) -> str:
        """Generate a brief Chinese summary for the news dimension."""
        if count == 0:
            return "近期無相關新聞報導。"

        parts = []
        if score >= 30:
            parts.append(f"近期 {count} 則新聞整體偏正面")
        elif score >= 10:
            parts.append(f"近期 {count} 則新聞略偏正面")
        elif score >= -10:
            parts.append(f"近期 {count} 則新聞立場中性")
        elif score >= -30:
            parts.append(f"近期 {count} 則新聞略偏負面")
        else:
            parts.append(f"近期 {count} 則新聞整體偏負面")

        heat_desc = {"hot": "，社群關注度高", "normal": "", "cold": "，社群關注度低"}
        parts.append(heat_desc.get(heat, "") + "。")

        return "".join(parts)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

analysis_engine = AnalysisEngine()
