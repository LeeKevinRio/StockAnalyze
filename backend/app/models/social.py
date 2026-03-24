"""Social media and aggregated sentiment models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SocialPost(Base):
    """Social media posts (PTT, Dcard, etc.)."""

    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # ptt, dcard
    board: Mapped[str | None] = mapped_column(String(50))  # Stock, Tech_Job
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(String(1000))
    mentioned_stocks: Mapped[dict | None] = mapped_column(JSONB, default=list)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    push_count: Mapped[int] = mapped_column(Integer, default=0)
    boo_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StockSentiment(Base):
    """Daily aggregated sentiment scores per stock."""

    __tablename__ = "stock_sentiments"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", "source_type", name="uq_stock_sentiment_date_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # news, social, combined
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    heat_level: Mapped[str | None] = mapped_column(String(20))  # hot, normal, cold
