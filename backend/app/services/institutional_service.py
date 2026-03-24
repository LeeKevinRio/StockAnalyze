"""Institutional and margin trading analysis service.

Fetches data from the database and analyses institutional investor
behaviour, margin trading patterns, and chip distribution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institutional import InstitutionalTrading, MarginTrading

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class InstitutionalResult:
    """Analysis result for three institutional investors."""

    foreign_trend: str = "neutral"  # "buying", "selling", "neutral"
    trust_trend: str = "neutral"
    dealer_trend: str = "neutral"
    foreign_consecutive_days: int = 0  # positive = buying, negative = selling
    trust_consecutive_days: int = 0
    cumulative_foreign_5d: int = 0
    cumulative_foreign_10d: int = 0
    cumulative_foreign_20d: int = 0
    cumulative_trust_5d: int = 0
    cumulative_trust_10d: int = 0
    cumulative_trust_20d: int = 0
    cumulative_dealer_20d: int = 0
    raw_data: list[dict] = field(default_factory=list)


@dataclass
class MarginResult:
    """Analysis result for margin / short trading."""

    margin_trend: str = "stable"  # "increasing", "decreasing", "stable"
    short_trend: str = "stable"
    utilization_level: str = "low"  # "high", "medium", "low"
    squeeze_potential: bool = False
    margin_balance_change_pct: float = 0.0  # % change over period
    short_balance_change_pct: float = 0.0
    latest_utilization: float = 0.0
    raw_data: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class InstitutionalService:
    """Analyse institutional trading patterns and chip distribution."""

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    async def get_institutional_data(
        self,
        stock_id: str,
        db: AsyncSession,
        days: int = 30,
    ) -> list[dict]:
        """Fetch institutional trading records from the database.

        Returns list of dicts sorted by date ascending.
        """
        stmt = (
            select(InstitutionalTrading)
            .where(InstitutionalTrading.stock_id == stock_id)
            .order_by(InstitutionalTrading.date.desc())
            .limit(days)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        data = []
        for row in reversed(rows):  # oldest first
            data.append({
                "date": row.date.isoformat() if row.date else "",
                "foreign_buy": row.foreign_buy or 0,
                "foreign_sell": row.foreign_sell or 0,
                "foreign_net": row.foreign_net or 0,
                "trust_buy": row.trust_buy or 0,
                "trust_sell": row.trust_sell or 0,
                "trust_net": row.trust_net or 0,
                "dealer_buy": row.dealer_buy or 0,
                "dealer_sell": row.dealer_sell or 0,
                "dealer_net": row.dealer_net or 0,
                "total_net": row.total_net or 0,
            })
        return data

    async def get_margin_data(
        self,
        stock_id: str,
        db: AsyncSession,
        days: int = 30,
    ) -> list[dict]:
        """Fetch margin trading records from the database.

        Returns list of dicts sorted by date ascending.
        """
        stmt = (
            select(MarginTrading)
            .where(MarginTrading.stock_id == stock_id)
            .order_by(MarginTrading.date.desc())
            .limit(days)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        data = []
        for row in reversed(rows):  # oldest first
            data.append({
                "date": row.date.isoformat() if row.date else "",
                "margin_buy": row.margin_buy or 0,
                "margin_sell": row.margin_sell or 0,
                "margin_balance": row.margin_balance or 0,
                "margin_utilization": float(row.margin_utilization) if row.margin_utilization else 0.0,
                "short_sell": row.short_sell or 0,
                "short_buy": row.short_buy or 0,
                "short_balance": row.short_balance or 0,
            })
        return data

    # ------------------------------------------------------------------
    # Institutional analysis
    # ------------------------------------------------------------------

    def analyze_institutional(self, data: list[dict]) -> InstitutionalResult:
        """Analyse institutional trading patterns.

        Computes cumulative net values, consecutive day streaks,
        and trend classification for each investor type.
        """
        if not data:
            return InstitutionalResult()

        n = len(data)

        # Cumulative net values
        foreign_nets = [d["foreign_net"] for d in data]
        trust_nets = [d["trust_net"] for d in data]
        dealer_nets = [d["dealer_net"] for d in data]

        cum_foreign_5d = sum(foreign_nets[-5:]) if n >= 1 else 0
        cum_foreign_10d = sum(foreign_nets[-10:]) if n >= 1 else 0
        cum_foreign_20d = sum(foreign_nets[-20:]) if n >= 1 else 0

        cum_trust_5d = sum(trust_nets[-5:]) if n >= 1 else 0
        cum_trust_10d = sum(trust_nets[-10:]) if n >= 1 else 0
        cum_trust_20d = sum(trust_nets[-20:]) if n >= 1 else 0

        cum_dealer_20d = sum(dealer_nets[-20:]) if n >= 1 else 0

        # Consecutive buying/selling days
        foreign_consec = self._consecutive_days(foreign_nets)
        trust_consec = self._consecutive_days(trust_nets)

        # Trend classification
        foreign_trend = self._classify_trend(cum_foreign_5d, cum_foreign_10d, cum_foreign_20d)
        trust_trend = self._classify_trend(cum_trust_5d, cum_trust_10d, cum_trust_20d)
        dealer_trend = self._classify_trend(
            sum(dealer_nets[-5:]) if n >= 1 else 0,
            sum(dealer_nets[-10:]) if n >= 1 else 0,
            cum_dealer_20d,
        )

        return InstitutionalResult(
            foreign_trend=foreign_trend,
            trust_trend=trust_trend,
            dealer_trend=dealer_trend,
            foreign_consecutive_days=foreign_consec,
            trust_consecutive_days=trust_consec,
            cumulative_foreign_5d=cum_foreign_5d,
            cumulative_foreign_10d=cum_foreign_10d,
            cumulative_foreign_20d=cum_foreign_20d,
            cumulative_trust_5d=cum_trust_5d,
            cumulative_trust_10d=cum_trust_10d,
            cumulative_trust_20d=cum_trust_20d,
            cumulative_dealer_20d=cum_dealer_20d,
            raw_data=data,
        )

    # ------------------------------------------------------------------
    # Margin analysis
    # ------------------------------------------------------------------

    def analyze_margin(self, data: list[dict]) -> MarginResult:
        """Analyse margin / short trading patterns."""
        if not data:
            return MarginResult()

        n = len(data)

        # Margin balance trend
        margin_balances = [d["margin_balance"] for d in data]
        margin_trend = self._balance_trend(margin_balances)

        # Short balance trend
        short_balances = [d["short_balance"] for d in data]
        short_trend = self._balance_trend(short_balances)

        # Utilization level
        latest_util = data[-1].get("margin_utilization", 0.0)
        if latest_util >= 60:
            util_level = "high"
        elif latest_util >= 30:
            util_level = "medium"
        else:
            util_level = "low"

        # Balance change percentages
        margin_change_pct = self._pct_change(margin_balances)
        short_change_pct = self._pct_change(short_balances)

        # Short squeeze potential: short balance significantly high and increasing
        squeeze = False
        if n >= 5:
            recent_short = short_balances[-1]
            avg_short = sum(short_balances[-10:]) / min(10, n)
            if avg_short > 0 and recent_short > avg_short * 1.2 and short_trend == "increasing":
                squeeze = True

        return MarginResult(
            margin_trend=margin_trend,
            short_trend=short_trend,
            utilization_level=util_level,
            squeeze_potential=squeeze,
            margin_balance_change_pct=round(margin_change_pct, 2),
            short_balance_change_pct=round(short_change_pct, 2),
            latest_utilization=round(latest_util, 2),
            raw_data=data,
        )

    # ------------------------------------------------------------------
    # Score calculation
    # ------------------------------------------------------------------

    def calculate_score(
        self,
        institutional: InstitutionalResult,
        margin: MarginResult,
    ) -> float:
        """Calculate institutional dimension score (-100 to +100).

        Scoring breakdown:
        - Foreign 20d net trend: +/-25
        - Trust 20d net trend: +/-15
        - Foreign + Trust synergy bonus: +/-10
        - Consecutive foreign buying/selling 5+ days: +/-10
        - Margin balance trend: +/-10
        - Margin FOMO surge: -10
        - Short balance signal: -5
        """
        score = 0.0

        # --- Foreign investor 20d ---
        if institutional.cumulative_foreign_20d > 0:
            if institutional.foreign_trend == "buying":
                score += 25
            else:
                score += 10  # positive but not strong trend
        elif institutional.cumulative_foreign_20d < 0:
            if institutional.foreign_trend == "selling":
                score -= 25
            else:
                score -= 10

        # --- Trust 20d ---
        if institutional.cumulative_trust_20d > 0:
            if institutional.trust_trend == "buying":
                score += 15
            else:
                score += 5
        elif institutional.cumulative_trust_20d < 0:
            if institutional.trust_trend == "selling":
                score -= 15
            else:
                score -= 5

        # --- Synergy bonus ---
        both_buying = (
            institutional.foreign_trend == "buying"
            and institutional.trust_trend == "buying"
        )
        both_selling = (
            institutional.foreign_trend == "selling"
            and institutional.trust_trend == "selling"
        )
        if both_buying:
            score += 10
        elif both_selling:
            score -= 10

        # --- Consecutive days ---
        if institutional.foreign_consecutive_days >= 5:
            score += 10
        elif institutional.foreign_consecutive_days <= -5:
            score -= 10

        # --- Margin balance trend ---
        if margin.margin_trend == "decreasing":
            score += 5  # deleveraging is positive
        elif margin.margin_trend == "increasing":
            # Check for FOMO surge (large increase)
            if margin.margin_balance_change_pct > 20:
                score -= 10  # retail FOMO
            else:
                score -= 5

        # --- Short balance ---
        if margin.short_trend == "increasing":
            score -= 5
        if margin.squeeze_potential:
            score += 5  # squeeze could push price up

        return max(-100.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Summary generation
    # ------------------------------------------------------------------

    def generate_summary(
        self,
        score: float,
        institutional: InstitutionalResult,
        margin: MarginResult,
    ) -> str:
        """Generate a Chinese text summary of the institutional analysis."""
        # Overall assessment
        if score >= 40:
            overall = "法人籌碼面強勢偏多"
        elif score >= 10:
            overall = "法人籌碼面略偏多"
        elif score >= -10:
            overall = "法人籌碼面中性"
        elif score >= -40:
            overall = "法人籌碼面略偏空"
        else:
            overall = "法人籌碼面弱勢偏空"

        parts = [f"【籌碼評分 {score:+.0f}】{overall}。"]

        # Foreign investor
        if institutional.foreign_trend == "buying":
            streak = ""
            if institutional.foreign_consecutive_days > 0:
                streak = f"，已連續買超 {institutional.foreign_consecutive_days} 日"
            parts.append(f"外資近期持續買超{streak}，20日累計淨買 {institutional.cumulative_foreign_20d:,} 張。")
        elif institutional.foreign_trend == "selling":
            streak = ""
            if institutional.foreign_consecutive_days < 0:
                streak = f"，已連續賣超 {abs(institutional.foreign_consecutive_days)} 日"
            parts.append(f"外資近期持續賣超{streak}，20日累計淨賣 {abs(institutional.cumulative_foreign_20d):,} 張。")
        else:
            parts.append("外資近期買賣態度中立。")

        # Trust
        if institutional.trust_trend == "buying":
            parts.append(f"投信持續加碼，20日累計淨買 {institutional.cumulative_trust_20d:,} 張。")
        elif institutional.trust_trend == "selling":
            parts.append(f"投信持續減碼，20日累計淨賣 {abs(institutional.cumulative_trust_20d):,} 張。")

        # Margin
        if margin.margin_trend == "increasing" and margin.margin_balance_change_pct > 10:
            parts.append("融資餘額明顯增加，散戶追買氣氛濃厚，需留意過熱風險。")
        elif margin.margin_trend == "decreasing":
            parts.append("融資餘額下降，籌碼沉澱有利後續走勢。")

        if margin.squeeze_potential:
            parts.append("融券餘額偏高且持續增加，存在軋空可能性。")

        return "".join(parts)

    # ==================================================================
    # Private helpers
    # ==================================================================

    @staticmethod
    def _consecutive_days(nets: list[int]) -> int:
        """Count consecutive buying (positive) or selling (negative) days
        from the most recent day backwards.

        Returns positive int for buying streak, negative for selling streak.
        """
        if not nets:
            return 0

        count = 0
        direction = 0  # 0 = undecided

        for val in reversed(nets):
            if direction == 0:
                if val > 0:
                    direction = 1
                    count = 1
                elif val < 0:
                    direction = -1
                    count = 1
                else:
                    # Zero net -- skip (doesn't break streak)
                    continue
            else:
                if direction == 1 and val > 0:
                    count += 1
                elif direction == -1 and val < 0:
                    count += 1
                else:
                    break

        return count * direction

    @staticmethod
    def _classify_trend(
        cum_5d: int,
        cum_10d: int,
        cum_20d: int,
    ) -> str:
        """Classify institutional trend as buying / selling / neutral."""
        # Strong buying: 5d, 10d, 20d all positive and 5d > 10d/2
        if cum_20d > 0 and cum_10d > 0 and cum_5d > 0:
            return "buying"
        # Strong selling: all negative
        if cum_20d < 0 and cum_10d < 0 and cum_5d < 0:
            return "selling"
        # Mixed
        positive_count = sum(1 for v in (cum_5d, cum_10d, cum_20d) if v > 0)
        if positive_count >= 2:
            return "buying"
        negative_count = sum(1 for v in (cum_5d, cum_10d, cum_20d) if v < 0)
        if negative_count >= 2:
            return "selling"
        return "neutral"

    @staticmethod
    def _balance_trend(balances: list[int]) -> str:
        """Determine trend of a balance series (margin or short)."""
        if len(balances) < 5:
            return "stable"

        recent_avg = sum(balances[-5:]) / 5
        earlier_avg = sum(balances[-10:-5]) / max(1, min(5, len(balances) - 5))

        if earlier_avg == 0:
            return "stable"

        change = (recent_avg - earlier_avg) / abs(earlier_avg)
        if change > 0.05:
            return "increasing"
        elif change < -0.05:
            return "decreasing"
        return "stable"

    @staticmethod
    def _pct_change(values: list[int]) -> float:
        """Percentage change between first and last value in the series."""
        if len(values) < 2 or values[0] == 0:
            return 0.0
        return ((values[-1] - values[0]) / abs(values[0])) * 100


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

institutional_service = InstitutionalService()
