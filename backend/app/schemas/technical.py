"""Technical analysis Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel


class TechnicalSignal(BaseModel):
    """A single buy/sell signal detected from technical indicators."""

    signal_type: str  # "ma_crossover", "macd_crossover", "rsi_oversold", etc.
    direction: str  # "bullish" or "bearish"
    description: str  # Chinese description
    strength: str  # "strong", "medium", "weak"


class TechnicalIndicatorsResponse(BaseModel):
    """Full technical analysis response for a stock."""

    stock_id: str
    indicators: dict  # MA, MACD, RSI, KD, Bollinger values
    signals: list[TechnicalSignal]
    score: float
    summary: str


class TechnicalSignalsResponse(BaseModel):
    """Signals-only response for a stock."""

    stock_id: str
    signals: list[TechnicalSignal]
    score: float
    summary: str
