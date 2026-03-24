"""News-related Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class NewsResponse(BaseModel):
    id: int
    stock_id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[Decimal] = None
    impact_level: Optional[str] = None
    published_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NewsSentimentTrend(BaseModel):
    date: str
    sentiment_score: float
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
