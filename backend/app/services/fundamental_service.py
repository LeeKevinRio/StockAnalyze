"""Fundamental analysis service — valuation, growth, and profitability scoring.

Provides comprehensive fundamental analysis for Taiwan-listed stocks including
PE/PB valuation, EPS and revenue growth trends, profitability margins, ROE
levels, dividend yield, and industry peer comparison.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundamental import FinancialStatement, StockDividend, StockFundamental
from app.models.stock import Stock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FundamentalResult:
    """Structured output from fundamental analysis."""

    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps: Optional[float] = None
    eps_growth_qoq: Optional[float] = None
    eps_growth_yoy: Optional[float] = None
    revenue_growth_mom: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[float] = None
    industry_pe_avg: Optional[float] = None
    industry_pb_avg: Optional[float] = None
    industry_roe_avg: Optional[float] = None
    operating_cash_flow_positive: Optional[bool] = None
    debt_ratio: Optional[float] = None
    valuation_assessment: str = "資料不足"
    growth_assessment: str = "資料不足"
    profitability_assessment: str = "資料不足"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FundamentalService:
    """Analyze stock fundamentals: valuation, growth, profitability."""

    # ---- Data retrieval methods -------------------------------------------

    async def get_fundamentals(self, stock_id: str, db: AsyncSession) -> dict:
        """Get latest fundamental data from DB.

        Args:
            stock_id: Taiwan stock ID (e.g. ``"2330"``).
            db: Async database session.

        Returns:
            Dict of fundamental metrics, or empty dict if no data.
        """
        stmt = (
            select(StockFundamental)
            .where(StockFundamental.stock_id == stock_id)
            .order_by(StockFundamental.report_date.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()

        if not row:
            return {}

        return {
            "stock_id": row.stock_id,
            "report_date": row.report_date.isoformat() if row.report_date else None,
            "pe_ratio": _to_float(row.pe_ratio),
            "pb_ratio": _to_float(row.pb_ratio),
            "ps_ratio": _to_float(row.ps_ratio),
            "eps": _to_float(row.eps),
            "roe": _to_float(row.roe),
            "roa": _to_float(row.roa),
            "revenue": _to_float(row.revenue),
            "gross_margin": _to_float(row.gross_margin),
            "operating_margin": _to_float(row.operating_margin),
            "net_margin": _to_float(row.net_margin),
            "market_cap": _to_float(row.market_cap),
        }

    async def get_financial_statements(
        self, stock_id: str, db: AsyncSession, quarters: int = 8
    ) -> list[dict]:
        """Get recent quarterly financial statements.

        Args:
            stock_id: Taiwan stock ID.
            db: Async database session.
            quarters: Number of recent quarters to retrieve.

        Returns:
            List of dicts ordered from newest to oldest quarter.
        """
        stmt = (
            select(FinancialStatement)
            .where(FinancialStatement.stock_id == stock_id)
            .order_by(
                FinancialStatement.report_year.desc(),
                FinancialStatement.report_quarter.desc(),
            )
            .limit(quarters)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        statements = []
        for row in rows:
            revenue = _to_float(row.revenue)
            gross_profit = _to_float(row.gross_profit)
            operating_income = _to_float(row.operating_income)
            net_income = _to_float(row.net_income)
            total_equity = _to_float(row.total_equity)

            # Compute margins
            gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit else None
            operating_margin = (operating_income / revenue * 100) if revenue and operating_income else None
            net_margin = (net_income / revenue * 100) if revenue and net_income else None

            # Approximate quarterly EPS (net_income / equity is ROE, not EPS)
            # We store EPS separately in fundamentals; here we just pass raw data
            statements.append({
                "year": row.report_year,
                "quarter": row.report_quarter,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "net_income": net_income,
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
                "net_margin": net_margin,
                "total_assets": _to_float(row.total_assets),
                "total_equity": total_equity,
                "operating_cash_flow": _to_float(row.operating_cash_flow),
                "free_cash_flow": _to_float(row.free_cash_flow),
            })

        return statements

    async def get_dividends(
        self, stock_id: str, db: AsyncSession, years: int = 5
    ) -> list[dict]:
        """Get dividend history.

        Args:
            stock_id: Taiwan stock ID.
            db: Async database session.
            years: Number of years of history.

        Returns:
            List of dicts ordered from newest to oldest year.
        """
        stmt = (
            select(StockDividend)
            .where(StockDividend.stock_id == stock_id)
            .order_by(StockDividend.year.desc())
            .limit(years)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "year": row.year,
                "cash_dividend": _to_float(row.cash_dividend),
                "stock_dividend": _to_float(row.stock_dividend),
                "dividend_yield": _to_float(row.dividend_yield),
                "ex_dividend_date": row.ex_dividend_date.isoformat() if row.ex_dividend_date else None,
            }
            for row in rows
        ]

    async def get_peer_stocks(
        self, stock_id: str, db: AsyncSession
    ) -> list[dict]:
        """Get stocks in the same industry for comparison.

        Args:
            stock_id: Taiwan stock ID.
            db: Async database session.

        Returns:
            List of peer stock dicts with their fundamental metrics.
        """
        # Find the target stock's industry
        stock_stmt = select(Stock).where(Stock.stock_id == stock_id)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if not stock or not stock.industry:
            return []

        # Get all stocks in the same industry (excluding target)
        peers_stmt = (
            select(Stock)
            .where(Stock.industry == stock.industry, Stock.stock_id != stock_id)
            .limit(20)
        )
        peers_result = await db.execute(peers_stmt)
        peer_stocks = peers_result.scalars().all()

        peers = []
        for peer in peer_stocks:
            # Get latest fundamentals for each peer
            fund_stmt = (
                select(StockFundamental)
                .where(StockFundamental.stock_id == peer.stock_id)
                .order_by(StockFundamental.report_date.desc())
                .limit(1)
            )
            fund_result = await db.execute(fund_stmt)
            fund = fund_result.scalar_one_or_none()

            peers.append({
                "stock_id": peer.stock_id,
                "stock_name": peer.name,
                "pe_ratio": _to_float(fund.pe_ratio) if fund else None,
                "pb_ratio": _to_float(fund.pb_ratio) if fund else None,
                "roe": _to_float(fund.roe) if fund else None,
                "eps": _to_float(fund.eps) if fund else None,
                "gross_margin": _to_float(fund.gross_margin) if fund else None,
                "dividend_yield": _to_float(fund.dividend_yield) if fund and hasattr(fund, "dividend_yield") else None,
                "market_cap": _to_float(fund.market_cap) if fund else None,
            })

        return peers

    # ---- Analysis methods ------------------------------------------------

    def analyze(
        self,
        fundamentals: dict,
        statements: list[dict],
        dividends: list[dict],
        peers: list[dict],
    ) -> FundamentalResult:
        """Run full fundamental analysis.

        Combines valuation assessment, growth trends, profitability metrics,
        and peer comparison into a structured result.

        Args:
            fundamentals: Latest fundamental metrics dict.
            statements: Recent quarterly financial statements.
            dividends: Dividend history.
            peers: Peer stock data.

        Returns:
            FundamentalResult with all analysis fields populated.
        """
        result = FundamentalResult()

        # --- Pull core metrics from fundamentals ---
        result.pe_ratio = fundamentals.get("pe_ratio")
        result.pb_ratio = fundamentals.get("pb_ratio")
        result.eps = fundamentals.get("eps")
        result.roe = fundamentals.get("roe")
        result.roa = fundamentals.get("roa")
        result.gross_margin = fundamentals.get("gross_margin")
        result.operating_margin = fundamentals.get("operating_margin")
        result.net_margin = fundamentals.get("net_margin")
        result.market_cap = fundamentals.get("market_cap")

        # --- Growth from financial statements ---
        if len(statements) >= 2:
            curr = statements[0]
            prev_q = statements[1]

            # EPS growth QoQ (using net_income as proxy)
            if curr.get("net_income") and prev_q.get("net_income") and prev_q["net_income"] != 0:
                result.eps_growth_qoq = (
                    (curr["net_income"] - prev_q["net_income"]) / abs(prev_q["net_income"]) * 100
                )

            # Revenue growth MoM (quarter-over-quarter)
            if curr.get("revenue") and prev_q.get("revenue") and prev_q["revenue"] != 0:
                result.revenue_growth_mom = (
                    (curr["revenue"] - prev_q["revenue"]) / abs(prev_q["revenue"]) * 100
                )

        # YoY growth: compare same quarter last year
        if len(statements) >= 5:
            curr = statements[0]
            prev_y = statements[4]  # Same quarter, one year ago

            if curr.get("net_income") and prev_y.get("net_income") and prev_y["net_income"] != 0:
                result.eps_growth_yoy = (
                    (curr["net_income"] - prev_y["net_income"]) / abs(prev_y["net_income"]) * 100
                )

            if curr.get("revenue") and prev_y.get("revenue") and prev_y["revenue"] != 0:
                result.revenue_growth_yoy = (
                    (curr["revenue"] - prev_y["revenue"]) / abs(prev_y["revenue"]) * 100
                )

        # --- Operating cash flow direction ---
        if statements and statements[0].get("operating_cash_flow") is not None:
            result.operating_cash_flow_positive = statements[0]["operating_cash_flow"] > 0

        # --- Debt ratio from latest statement ---
        if statements:
            latest = statements[0]
            assets = latest.get("total_assets")
            equity = latest.get("total_equity")
            if assets and equity and assets > 0:
                result.debt_ratio = ((assets - equity) / assets) * 100

        # --- Dividend yield ---
        if dividends:
            latest_div = dividends[0]
            result.dividend_yield = latest_div.get("dividend_yield")

        # --- Industry peer averages ---
        if peers:
            pe_values = [p["pe_ratio"] for p in peers if p.get("pe_ratio") and p["pe_ratio"] > 0]
            pb_values = [p["pb_ratio"] for p in peers if p.get("pb_ratio") and p["pb_ratio"] > 0]
            roe_values = [p["roe"] for p in peers if p.get("roe") is not None]

            if pe_values:
                result.industry_pe_avg = sum(pe_values) / len(pe_values)
            if pb_values:
                result.industry_pb_avg = sum(pb_values) / len(pb_values)
            if roe_values:
                result.industry_roe_avg = sum(roe_values) / len(roe_values)

        # --- Assessments ---
        result.valuation_assessment = self._assess_valuation(result)
        result.growth_assessment = self._assess_growth(result)
        result.profitability_assessment = self._assess_profitability(result)

        return result

    def calculate_score(self, analysis: FundamentalResult) -> float:
        """Calculate fundamental dimension score (-100 to +100).

        Scoring criteria:
        - PE ratio vs industry avg: below avg = +15, significantly below = +25, above = -10
        - EPS growth (QoQ, YoY): growing = +20, declining = -20
        - Revenue growth (MoM, YoY): growing = +15, declining = -15
        - Gross margin trend: improving = +10, declining = -10
        - ROE level: >15% = +10, >20% = +15, <5% = -10
        - Dividend yield: >4% = +10, >6% = +15
        - Debt ratio: low (<30%) = +5
        - Cash flow: positive operating CF = +5, negative = -10

        Returns:
            Score clamped to [-100, +100].
        """
        score = 0.0

        # PE ratio vs industry average
        if analysis.pe_ratio is not None and analysis.industry_pe_avg is not None:
            if analysis.industry_pe_avg > 0:
                ratio = analysis.pe_ratio / analysis.industry_pe_avg
                if ratio < 0.7:
                    score += 25  # Significantly undervalued
                elif ratio < 1.0:
                    score += 15  # Below industry average
                elif ratio > 1.5:
                    score -= 15  # Significantly overvalued
                elif ratio > 1.0:
                    score -= 10  # Above industry average
        elif analysis.pe_ratio is not None:
            # No industry avg available; use absolute thresholds
            if 0 < analysis.pe_ratio < 12:
                score += 15
            elif analysis.pe_ratio > 30:
                score -= 10

        # EPS growth
        if analysis.eps_growth_yoy is not None:
            if analysis.eps_growth_yoy > 20:
                score += 20
            elif analysis.eps_growth_yoy > 5:
                score += 10
            elif analysis.eps_growth_yoy < -20:
                score -= 20
            elif analysis.eps_growth_yoy < -5:
                score -= 10
        elif analysis.eps_growth_qoq is not None:
            if analysis.eps_growth_qoq > 15:
                score += 15
            elif analysis.eps_growth_qoq > 0:
                score += 5
            elif analysis.eps_growth_qoq < -15:
                score -= 15
            elif analysis.eps_growth_qoq < 0:
                score -= 5

        # Revenue growth
        if analysis.revenue_growth_yoy is not None:
            if analysis.revenue_growth_yoy > 15:
                score += 15
            elif analysis.revenue_growth_yoy > 5:
                score += 8
            elif analysis.revenue_growth_yoy < -15:
                score -= 15
            elif analysis.revenue_growth_yoy < -5:
                score -= 8
        elif analysis.revenue_growth_mom is not None:
            if analysis.revenue_growth_mom > 10:
                score += 10
            elif analysis.revenue_growth_mom > 0:
                score += 3
            elif analysis.revenue_growth_mom < -10:
                score -= 10
            elif analysis.revenue_growth_mom < 0:
                score -= 3

        # Gross margin (profitability indicator)
        if analysis.gross_margin is not None:
            if analysis.gross_margin > 40:
                score += 10
            elif analysis.gross_margin > 25:
                score += 5
            elif analysis.gross_margin < 10:
                score -= 10

        # ROE level
        if analysis.roe is not None:
            if analysis.roe > 20:
                score += 15
            elif analysis.roe > 15:
                score += 10
            elif analysis.roe > 10:
                score += 5
            elif analysis.roe < 5:
                score -= 10

        # Dividend yield
        if analysis.dividend_yield is not None:
            if analysis.dividend_yield > 6:
                score += 15
            elif analysis.dividend_yield > 4:
                score += 10
            elif analysis.dividend_yield > 2:
                score += 5

        # Debt ratio
        if analysis.debt_ratio is not None:
            if analysis.debt_ratio < 30:
                score += 5
            elif analysis.debt_ratio > 70:
                score -= 10

        # Operating cash flow
        if analysis.operating_cash_flow_positive is not None:
            if analysis.operating_cash_flow_positive:
                score += 5
            else:
                score -= 10

        return max(-100.0, min(100.0, score))

    def generate_summary(self, score: float, analysis: FundamentalResult) -> str:
        """Generate Chinese text summary of fundamental analysis.

        Args:
            score: The calculated fundamental score.
            analysis: Full FundamentalResult.

        Returns:
            Summary string in Traditional Chinese.
        """
        parts = []

        # Overall assessment
        if score >= 40:
            parts.append("基本面表現強勁，具備良好投資價值。")
        elif score >= 15:
            parts.append("基本面表現穩健，整體財務狀況良好。")
        elif score >= -15:
            parts.append("基本面表現中性，無明顯利多或利空。")
        elif score >= -40:
            parts.append("基本面偏弱，需留意財務風險。")
        else:
            parts.append("基本面表現疲弱，多項指標顯示警訊。")

        # Valuation
        parts.append(f"估值面：{analysis.valuation_assessment}")

        # Growth
        parts.append(f"成長力：{analysis.growth_assessment}")

        # Profitability
        parts.append(f"獲利能力：{analysis.profitability_assessment}")

        # Key metrics
        metrics = []
        if analysis.pe_ratio is not None:
            metrics.append(f"本益比 {analysis.pe_ratio:.1f}")
        if analysis.roe is not None:
            metrics.append(f"ROE {analysis.roe:.1f}%")
        if analysis.dividend_yield is not None:
            metrics.append(f"殖利率 {analysis.dividend_yield:.1f}%")
        if metrics:
            parts.append(f"關鍵指標：{'、'.join(metrics)}。")

        return " ".join(parts)

    # ---- Private assessment helpers --------------------------------------

    @staticmethod
    def _assess_valuation(result: FundamentalResult) -> str:
        """Assess valuation level relative to peers and absolute thresholds."""
        if result.pe_ratio is None:
            return "本益比資料不足，無法評估估值水平"

        pe = result.pe_ratio
        industry_pe = result.industry_pe_avg

        if industry_pe and industry_pe > 0:
            ratio = pe / industry_pe
            if ratio < 0.7:
                return f"本益比 {pe:.1f} 遠低於產業平均 {industry_pe:.1f}，估值偏低具吸引力"
            elif ratio < 0.9:
                return f"本益比 {pe:.1f} 略低於產業平均 {industry_pe:.1f}，估值合理偏低"
            elif ratio < 1.1:
                return f"本益比 {pe:.1f} 接近產業平均 {industry_pe:.1f}，估值合理"
            elif ratio < 1.3:
                return f"本益比 {pe:.1f} 略高於產業平均 {industry_pe:.1f}，估值偏高"
            else:
                return f"本益比 {pe:.1f} 遠高於產業平均 {industry_pe:.1f}，估值偏貴"
        else:
            if pe < 10:
                return f"本益比 {pe:.1f}，估值偏低"
            elif pe < 20:
                return f"本益比 {pe:.1f}，估值合理"
            else:
                return f"本益比 {pe:.1f}，估值偏高"

    @staticmethod
    def _assess_growth(result: FundamentalResult) -> str:
        """Assess growth trajectory from EPS and revenue trends."""
        parts = []

        if result.eps_growth_yoy is not None:
            if result.eps_growth_yoy > 20:
                parts.append(f"每股盈餘年增率 {result.eps_growth_yoy:.1f}%，成長強勁")
            elif result.eps_growth_yoy > 0:
                parts.append(f"每股盈餘年增率 {result.eps_growth_yoy:.1f}%，持續成長")
            else:
                parts.append(f"每股盈餘年增率 {result.eps_growth_yoy:.1f}%，獲利衰退")

        if result.revenue_growth_yoy is not None:
            if result.revenue_growth_yoy > 15:
                parts.append(f"營收年增率 {result.revenue_growth_yoy:.1f}%，動能強勁")
            elif result.revenue_growth_yoy > 0:
                parts.append(f"營收年增率 {result.revenue_growth_yoy:.1f}%，穩步成長")
            else:
                parts.append(f"營收年增率 {result.revenue_growth_yoy:.1f}%，營收下滑")

        if not parts:
            return "成長相關資料不足"

        return "；".join(parts)

    @staticmethod
    def _assess_profitability(result: FundamentalResult) -> str:
        """Assess profitability from margins and ROE."""
        parts = []

        if result.gross_margin is not None:
            if result.gross_margin > 40:
                parts.append(f"毛利率 {result.gross_margin:.1f}% 表現優異")
            elif result.gross_margin > 20:
                parts.append(f"毛利率 {result.gross_margin:.1f}% 表現穩定")
            else:
                parts.append(f"毛利率 {result.gross_margin:.1f}% 偏低")

        if result.roe is not None:
            if result.roe > 20:
                parts.append(f"ROE {result.roe:.1f}% 資本運用效率卓越")
            elif result.roe > 15:
                parts.append(f"ROE {result.roe:.1f}% 資本運用效率良好")
            elif result.roe > 8:
                parts.append(f"ROE {result.roe:.1f}% 中等水準")
            else:
                parts.append(f"ROE {result.roe:.1f}% 偏低")

        if not parts:
            return "獲利相關資料不足"

        return "；".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(value: Decimal | float | int | None) -> Optional[float]:
    """Safely convert a Decimal or numeric value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

fundamental_service = FundamentalService()
