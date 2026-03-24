"""Institutional and margin trading models."""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InstitutionalTrading(Base):
    """Daily three institutional investors trading data."""

    __tablename__ = "institutional_trading"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_institutional_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    foreign_buy: Mapped[int | None] = mapped_column(BigInteger)
    foreign_sell: Mapped[int | None] = mapped_column(BigInteger)
    foreign_net: Mapped[int | None] = mapped_column(BigInteger)
    trust_buy: Mapped[int | None] = mapped_column(BigInteger)
    trust_sell: Mapped[int | None] = mapped_column(BigInteger)
    trust_net: Mapped[int | None] = mapped_column(BigInteger)
    dealer_buy: Mapped[int | None] = mapped_column(BigInteger)
    dealer_sell: Mapped[int | None] = mapped_column(BigInteger)
    dealer_net: Mapped[int | None] = mapped_column(BigInteger)
    total_net: Mapped[int | None] = mapped_column(BigInteger)


class MarginTrading(Base):
    """Daily margin trading data."""

    __tablename__ = "margin_trading"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_margin_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    margin_buy: Mapped[int | None] = mapped_column(BigInteger)
    margin_sell: Mapped[int | None] = mapped_column(BigInteger)
    margin_balance: Mapped[int | None] = mapped_column(BigInteger)
    margin_utilization: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    short_sell: Mapped[int | None] = mapped_column(BigInteger)
    short_buy: Mapped[int | None] = mapped_column(BigInteger)
    short_balance: Mapped[int | None] = mapped_column(BigInteger)
