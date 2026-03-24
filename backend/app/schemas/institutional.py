"""Institutional and margin trading Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel


class InstitutionalDayData(BaseModel):
    """Single day of institutional trading data."""

    date: str
    foreign_net: int
    trust_net: int
    dealer_net: int
    total_net: int


class InstitutionalAnalysis(BaseModel):
    """Institutional trading analysis results."""

    foreign_trend: str  # "buying", "selling", "neutral"
    trust_trend: str
    dealer_trend: str
    foreign_consecutive_days: int  # positive = buying streak, negative = selling streak
    cumulative_foreign_20d: int
    cumulative_trust_20d: int
    score: float
    summary: str


class InstitutionalDataResponse(BaseModel):
    """Full institutional trading data + analysis response."""

    stock_id: str
    data: list[InstitutionalDayData]
    analysis: InstitutionalAnalysis


class MarginDayData(BaseModel):
    """Single day of margin trading data."""

    date: str
    margin_balance: int
    margin_change: int
    short_balance: int
    short_change: int
    utilization: float


class MarginAnalysis(BaseModel):
    """Margin trading analysis results."""

    margin_trend: str  # "increasing", "decreasing", "stable"
    short_trend: str
    utilization_level: str  # "high", "medium", "low"
    squeeze_potential: bool
    summary: str


class MarginDataResponse(BaseModel):
    """Margin trading data + analysis response."""

    stock_id: str
    data: list[MarginDayData]
    analysis: MarginAnalysis


class InstitutionalSummaryResponse(BaseModel):
    """Quick summary combining institutional + margin analysis."""

    stock_id: str
    score: float
    signal: str  # "bullish", "bearish", "neutral"
    summary: str
    foreign_trend: str
    trust_trend: str
