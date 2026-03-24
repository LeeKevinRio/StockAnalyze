"""News article model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockNews(Base):
    """News articles with sentiment analysis."""

    __tablename__ = "stock_news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str | None] = mapped_column(String(10), index=True)  # nullable for market-wide news
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))  # google_news, cnyes, moneydj, yahoo
    source_url: Mapped[str | None] = mapped_column(String(1000))
    sentiment: Mapped[str | None] = mapped_column(String(20))  # positive, negative, neutral
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))  # -1.000 to +1.000
    sentiment_method: Mapped[str | None] = mapped_column(String(20))  # ai, keyword, hybrid
    impact_level: Mapped[str | None] = mapped_column(String(10))  # high, medium, low
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
