"""Macro economic analysis service.

Analyzes macroeconomic environment factors that impact Taiwan stock market
including interest rate direction, exchange rates, market index trends,
global volatility, and business cycle positioning.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import StockPrice

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class MacroIndicator:
    """A single macro indicator with value and trend."""

    name: str
    value: Optional[float] = None
    previous_value: Optional[float] = None
    change: Optional[float] = None
    trend: Optional[str] = None  # "rising", "falling", "stable"
    updated_at: Optional[str] = None


@dataclass
class MacroResult:
    """Structured output from macro environment analysis."""

    interest_rate: Optional[MacroIndicator] = None
    taiwan_rate: Optional[MacroIndicator] = None
    exchange_rate: Optional[MacroIndicator] = None
    taiex: Optional[MacroIndicator] = None
    vix: Optional[MacroIndicator] = None
    ten_year_treasury: Optional[MacroIndicator] = None

    rate_cycle: str = "holding"  # "cutting", "hiking", "holding"
    business_cycle: str = "unknown"  # "expansion", "contraction", "recovery", "slowdown"
    taiex_trend: str = "unknown"  # "uptrend", "downtrend", "sideways"
    vix_level: str = "normal"  # "low", "normal", "elevated", "high"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MacroService:
    """Analyze macroeconomic environment impact on stocks."""

    async def get_macro_indicators(self, db: AsyncSession) -> dict:
        """Get latest macro indicators from DB and external data.

        Attempts to gather macro data from FRED (via fred_fetcher) and
        local TAIEX prices. Returns a dict of all available indicators.

        Args:
            db: Async database session.

        Returns:
            Dict containing available macro indicator data.
        """
        indicators = {}

        # --- TAIEX index trend (use TAIEX as a stock_id or proxy) ---
        taiex_data = await self._get_taiex_data(db)
        if taiex_data:
            indicators["taiex"] = taiex_data

        # --- FRED data (if available) ---
        fred_data = await self._get_fred_data()
        indicators.update(fred_data)

        return indicators

    async def _get_taiex_data(self, db: AsyncSession) -> Optional[dict]:
        """Get TAIEX index data from stock prices as proxy.

        Looks for common TAIEX proxy stock IDs (e.g. 0050 ETF or
        direct index data if stored).

        Args:
            db: Async database session.

        Returns:
            Dict with TAIEX price info, or None.
        """
        # Try to get TAIEX data from a market index proxy
        # Common TAIEX proxies: "^TWII" or "0050" (Taiwan 50 ETF)
        for proxy_id in ("^TWII", "TAIEX", "0050"):
            stmt = (
                select(StockPrice)
                .where(StockPrice.stock_id == proxy_id)
                .order_by(StockPrice.date.desc())
                .limit(60)
            )
            result = await db.execute(stmt)
            rows = list(result.scalars().all())

            if rows:
                latest = rows[0]
                prices = [float(r.close) for r in rows if r.close]

                if len(prices) >= 2:
                    current = prices[0]
                    prev = prices[1]
                    change = current - prev

                    # Determine trend from MA20
                    ma20 = sum(prices[:20]) / min(20, len(prices[:20])) if len(prices) >= 5 else current
                    if current > ma20 * 1.02:
                        trend = "rising"
                    elif current < ma20 * 0.98:
                        trend = "falling"
                    else:
                        trend = "stable"

                    return {
                        "value": current,
                        "previous_value": prev,
                        "change": change,
                        "trend": trend,
                        "ma20": ma20,
                        "prices": prices[:60],
                    }

        return None

    async def _get_fred_data(self) -> dict:
        """Fetch macro indicators from FRED API.

        Returns:
            Dict of FRED-sourced indicators.
        """
        indicators = {}
        try:
            from app.data_fetchers.fred_fetcher import fred_fetcher

            # Federal Funds Rate
            fed_rate = await fred_fetcher.fetch_indicator("FEDFUNDS")
            if fed_rate:
                indicators["fed_rate"] = fed_rate

            # 10-Year Treasury
            treasury_10y = await fred_fetcher.fetch_indicator("DGS10")
            if treasury_10y:
                indicators["treasury_10y"] = treasury_10y

            # VIX
            vix = await fred_fetcher.fetch_indicator("VIXCLS")
            if vix:
                indicators["vix"] = vix

            # TWD/USD exchange rate
            exchange = await fred_fetcher.fetch_indicator("DEXTWUS")
            if exchange:
                indicators["exchange_rate"] = exchange

        except ImportError:
            logger.warning("fred_fetcher not available; skipping FRED data")
        except Exception as exc:
            logger.warning("Failed to fetch FRED data: %s", exc)

        return indicators

    def analyze(self, indicators: dict) -> MacroResult:
        """Analyze macro environment from collected indicators.

        Evaluates interest rate direction, exchange rate trends, market
        index behavior, global volatility, and business cycle position.

        Args:
            indicators: Dict of macro indicator data.

        Returns:
            MacroResult with all analysis fields populated.
        """
        result = MacroResult()

        # --- Interest Rate (Federal Funds Rate) ---
        fed_rate = indicators.get("fed_rate")
        if fed_rate and isinstance(fed_rate, dict):
            result.interest_rate = MacroIndicator(
                name="聯邦基金利率",
                value=fed_rate.get("value"),
                previous_value=fed_rate.get("previous_value"),
                change=fed_rate.get("change"),
                trend=fed_rate.get("trend"),
                updated_at=fed_rate.get("updated_at"),
            )
            # Determine rate cycle
            change = fed_rate.get("change", 0) or 0
            if change < -0.1:
                result.rate_cycle = "cutting"
            elif change > 0.1:
                result.rate_cycle = "hiking"
            else:
                result.rate_cycle = "holding"

        # --- 10-Year Treasury ---
        treasury = indicators.get("treasury_10y")
        if treasury and isinstance(treasury, dict):
            result.ten_year_treasury = MacroIndicator(
                name="美國10年期公債殖利率",
                value=treasury.get("value"),
                previous_value=treasury.get("previous_value"),
                change=treasury.get("change"),
                trend=treasury.get("trend"),
                updated_at=treasury.get("updated_at"),
            )

        # --- VIX ---
        vix = indicators.get("vix")
        if vix and isinstance(vix, dict):
            vix_value = vix.get("value")
            result.vix = MacroIndicator(
                name="VIX 恐慌指數",
                value=vix_value,
                previous_value=vix.get("previous_value"),
                change=vix.get("change"),
                trend=vix.get("trend"),
                updated_at=vix.get("updated_at"),
            )
            if vix_value is not None:
                if vix_value < 15:
                    result.vix_level = "low"
                elif vix_value < 20:
                    result.vix_level = "normal"
                elif vix_value < 30:
                    result.vix_level = "elevated"
                else:
                    result.vix_level = "high"

        # --- Exchange Rate (TWD/USD) ---
        exchange = indicators.get("exchange_rate")
        if exchange and isinstance(exchange, dict):
            result.exchange_rate = MacroIndicator(
                name="台幣/美元匯率",
                value=exchange.get("value"),
                previous_value=exchange.get("previous_value"),
                change=exchange.get("change"),
                trend=exchange.get("trend"),
                updated_at=exchange.get("updated_at"),
            )

        # --- TAIEX ---
        taiex = indicators.get("taiex")
        if taiex and isinstance(taiex, dict):
            result.taiex = MacroIndicator(
                name="加權指數",
                value=taiex.get("value"),
                previous_value=taiex.get("previous_value"),
                change=taiex.get("change"),
                trend=taiex.get("trend"),
            )
            trend = taiex.get("trend", "stable")
            if trend == "rising":
                result.taiex_trend = "uptrend"
            elif trend == "falling":
                result.taiex_trend = "downtrend"
            else:
                result.taiex_trend = "sideways"

        # --- Business cycle estimation ---
        result.business_cycle = self._estimate_business_cycle(indicators)

        return result

    def calculate_score(self, analysis: MacroResult) -> float:
        """Calculate macro dimension score (-100 to +100).

        Scoring:
        - Rate cutting cycle: +15 (good for stocks)
        - Rate hiking cycle: -15
        - Rate holding: +5 (stable)
        - TWD strengthening: mixed signal (0)
        - TWD weakening: -5 (bad for import-dependent)
        - TAIEX uptrend: +10
        - TAIEX downtrend: -10
        - Low VIX (<15): +5
        - Normal VIX (15-20): +3
        - Elevated VIX (20-30): -5
        - High VIX (>30): -10
        - Expansion phase: +10
        - Recovery phase: +5
        - Slowdown phase: -5
        - Contraction phase: -15

        Returns:
            Score clamped to [-100, +100].
        """
        score = 0.0

        # Interest rate cycle
        if analysis.rate_cycle == "cutting":
            score += 15
        elif analysis.rate_cycle == "hiking":
            score -= 15
        elif analysis.rate_cycle == "holding":
            score += 5

        # Exchange rate impact
        if analysis.exchange_rate and analysis.exchange_rate.trend:
            trend = analysis.exchange_rate.trend
            if trend == "falling":
                # TWD weakening vs USD => bad for imports, ok for exports
                score -= 5
            elif trend == "rising":
                # TWD strengthening => mixed
                score += 0

        # TAIEX trend
        if analysis.taiex_trend == "uptrend":
            score += 10
        elif analysis.taiex_trend == "downtrend":
            score -= 10

        # VIX level
        if analysis.vix_level == "low":
            score += 5
        elif analysis.vix_level == "normal":
            score += 3
        elif analysis.vix_level == "elevated":
            score -= 5
        elif analysis.vix_level == "high":
            score -= 10

        # Business cycle
        cycle_map = {
            "expansion": 10,
            "recovery": 5,
            "slowdown": -5,
            "contraction": -15,
        }
        score += cycle_map.get(analysis.business_cycle, 0)

        # 10-Year Treasury direction
        if analysis.ten_year_treasury and analysis.ten_year_treasury.trend:
            if analysis.ten_year_treasury.trend == "falling":
                score += 5  # Falling yields = bullish for stocks
            elif analysis.ten_year_treasury.trend == "rising":
                score -= 5  # Rising yields = bearish pressure

        return max(-100.0, min(100.0, score))

    def generate_summary(self, score: float, analysis: MacroResult) -> str:
        """Generate Chinese summary of macro environment analysis.

        Args:
            score: The calculated macro score.
            analysis: Full MacroResult.

        Returns:
            Summary string in Traditional Chinese.
        """
        parts = []

        # Overall assessment
        if score >= 20:
            parts.append("總體經濟環境對股市有利。")
        elif score >= 0:
            parts.append("總體經濟環境大致穩定，中性偏正面。")
        elif score >= -20:
            parts.append("總體經濟環境略偏保守，需留意風險。")
        else:
            parts.append("總體經濟環境嚴峻，逆風因素較多。")

        # Rate cycle
        cycle_desc = {
            "cutting": "目前處於降息循環，有利股市資金面",
            "hiking": "目前處於升息循環，對股市形成壓力",
            "holding": "利率維持穩定，市場觀望氣氛",
        }
        parts.append(f"利率環境：{cycle_desc.get(analysis.rate_cycle, '資料不足')}。")

        # TAIEX
        if analysis.taiex and analysis.taiex.value:
            trend_desc = {
                "uptrend": "呈上升趨勢",
                "downtrend": "呈下降趨勢",
                "sideways": "呈盤整格局",
            }
            parts.append(
                f"加權指數 {analysis.taiex.value:,.0f} 點，"
                f"{trend_desc.get(analysis.taiex_trend, '趨勢不明')}。"
            )

        # VIX
        vix_desc = {
            "low": "VIX 低檔，市場情緒樂觀",
            "normal": "VIX 正常區間",
            "elevated": "VIX 偏高，市場不確定性增加",
            "high": "VIX 高檔，市場恐慌情緒濃厚",
        }
        parts.append(f"{vix_desc.get(analysis.vix_level, 'VIX 資料不足')}。")

        # Business cycle
        cycle_names = {
            "expansion": "擴張期",
            "recovery": "復甦期",
            "slowdown": "趨緩期",
            "contraction": "收縮期",
        }
        bc = cycle_names.get(analysis.business_cycle)
        if bc:
            parts.append(f"景氣循環位置：{bc}。")

        return " ".join(parts)

    # ---- Private helpers -------------------------------------------------

    @staticmethod
    def _estimate_business_cycle(indicators: dict) -> str:
        """Estimate business cycle position from available indicators.

        Uses a simplified heuristic based on TAIEX trend and rate cycle.

        Returns:
            One of "expansion", "recovery", "slowdown", "contraction", "unknown".
        """
        taiex = indicators.get("taiex", {})
        fed_rate = indicators.get("fed_rate", {})

        taiex_trend = taiex.get("trend", "stable") if isinstance(taiex, dict) else "stable"
        rate_change = (fed_rate.get("change", 0) or 0) if isinstance(fed_rate, dict) else 0

        # Heuristic matrix:
        # TAIEX rising + rate cutting => recovery/expansion
        # TAIEX rising + rate holding/hiking => expansion
        # TAIEX falling + rate cutting => potential recovery
        # TAIEX falling + rate hiking => contraction
        # TAIEX stable => slowdown or holding

        if taiex_trend == "rising":
            if rate_change < -0.1:
                return "recovery"
            else:
                return "expansion"
        elif taiex_trend == "falling":
            if rate_change > 0.1:
                return "contraction"
            elif rate_change < -0.1:
                return "recovery"
            else:
                return "slowdown"
        else:
            # Sideways market
            if rate_change > 0.1:
                return "slowdown"
            elif rate_change < -0.1:
                return "recovery"
            return "unknown"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

macro_service = MacroService()
