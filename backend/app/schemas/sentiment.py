"""Sentiment-related Pydantic schemas."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SentimentSummary(BaseModel):
    stock_id: str
    date: date
    news_sentiment: Optional[Decimal] = None
    social_sentiment: Optional[Decimal] = None
    combined_sentiment: Optional[Decimal] = None
    mention_count: int = 0
    heat_level: Optional[str] = None


class SentimentTrend(BaseModel):
    date: str
    score: float
    source_type: str
    mention_count: int = 0


class HotStock(BaseModel):
    stock_id: str
    stock_name: str
    mention_count: int
    sentiment_score: float
    heat_level: str


class SocialPostResponse(BaseModel):
    id: int
    platform: str
    title: str
    author: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[Decimal] = None
    push_count: int = 0
    boo_count: int = 0
    posted_at: Optional[str] = None
    url: Optional[str] = None

    model_config = {"from_attributes": True}
