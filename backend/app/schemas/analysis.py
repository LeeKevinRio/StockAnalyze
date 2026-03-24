"""Analysis report Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DimensionScore(BaseModel):
    name: str
    score: float
    signal: str  # bullish, bearish, neutral
    key_factors: list[str] = []


class AnalysisScoresResponse(BaseModel):
    stock_id: str
    stock_name: str
    report_date: date
    overall_score: float
    overall_signal: str
    confidence: float
    dimensions: list[DimensionScore]


class AnalysisReportResponse(BaseModel):
    stock_id: str
    stock_name: str
    report_date: date
    overall_score: Optional[Decimal] = None
    overall_signal: Optional[str] = None
    confidence: Optional[Decimal] = None
    news_score: Optional[Decimal] = None
    fundamental_score: Optional[Decimal] = None
    technical_score: Optional[Decimal] = None
    institutional_score: Optional[Decimal] = None
    macro_score: Optional[Decimal] = None
    ai_report_markdown: Optional[str] = None
    ai_provider: Optional[str] = None
    risk_level: Optional[str] = None
    short_term_outlook: Optional[str] = None
    medium_term_outlook: Optional[str] = None
    long_term_outlook: Optional[str] = None
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
