"""Analysis report model - the core output of the platform."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisReport(Base):
    """Comprehensive multi-dimension analysis report."""

    __tablename__ = "analysis_reports"
    __table_args__ = (
        UniqueConstraint("stock_id", "report_date", name="uq_analysis_report_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Overall scores
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))  # -100 to +100
    overall_signal: Mapped[str | None] = mapped_column(String(20))  # strong_buy, buy, neutral, sell, strong_sell
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))  # 0.00 to 1.00

    # Dimension scores
    news_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    fundamental_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    institutional_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    macro_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))

    # Detailed breakdown
    dimension_details: Mapped[dict | None] = mapped_column(JSONB)

    # AI report
    ai_report_markdown: Mapped[str | None] = mapped_column(Text)
    ai_provider: Mapped[str | None] = mapped_column(String(50))

    # Outlook
    risk_level: Mapped[str | None] = mapped_column(String(20))  # high, medium, low
    short_term_outlook: Mapped[str | None] = mapped_column(Text)
    medium_term_outlook: Mapped[str | None] = mapped_column(Text)
    long_term_outlook: Mapped[str | None] = mapped_column(Text)

    # Price targets
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    stop_loss_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
