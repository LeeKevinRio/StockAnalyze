"""Fundamental analysis models."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockFundamental(Base):
    """Valuation snapshot."""

    __tablename__ = "stock_fundamentals"
    __table_args__ = (
        UniqueConstraint("stock_id", "report_date", name="uq_fundamental_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ps_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    roa: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    net_margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class FinancialStatement(Base):
    """Quarterly financial statements."""

    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "report_year", "report_quarter",
            name="uq_financial_statement_quarter",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    report_year: Mapped[int] = mapped_column(Integer, nullable=False)
    report_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    gross_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    operating_income: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    operating_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    free_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class StockDividend(Base):
    """Dividend history."""

    __tablename__ = "stock_dividends"
    __table_args__ = (
        UniqueConstraint("stock_id", "year", name="uq_dividend_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_dividend: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    stock_dividend: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ex_dividend_date: Mapped[date | None] = mapped_column(Date)
