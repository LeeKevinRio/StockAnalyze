"""Fundamental analysis Pydantic schemas."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class FundamentalDataResponse(BaseModel):
    """Core fundamental metrics for a stock."""

    stock_id: str
    stock_name: str
    report_date: Optional[date] = None

    # Valuation
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    market_cap: Optional[float] = None

    # Profitability
    eps: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None

    # Growth
    eps_growth_qoq: Optional[float] = None
    eps_growth_yoy: Optional[float] = None
    revenue_growth_mom: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None

    # Dividend
    dividend_yield: Optional[float] = None

    # Industry comparison
    industry: Optional[str] = None
    industry_pe_avg: Optional[float] = None

    # Analysis
    valuation_assessment: Optional[str] = None
    growth_assessment: Optional[str] = None
    profitability_assessment: Optional[str] = None
    score: Optional[float] = None
    summary: Optional[str] = None


class RevenueTrendItem(BaseModel):
    """Single month revenue data point."""

    year: int
    month: int
    revenue: Optional[float] = None
    revenue_yoy_growth: Optional[float] = None
    revenue_mom_growth: Optional[float] = None


class RevenueTrendResponse(BaseModel):
    """Monthly revenue trend for a stock."""

    stock_id: str
    stock_name: str
    data: list[RevenueTrendItem]


class FinancialStatementItem(BaseModel):
    """Single quarter financial statement."""

    year: int
    quarter: int
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None


class FinancialsResponse(BaseModel):
    """Quarterly financial statements for a stock."""

    stock_id: str
    stock_name: str
    statements: list[FinancialStatementItem]


class DividendItem(BaseModel):
    """Single year dividend data."""

    year: int
    cash_dividend: Optional[float] = None
    stock_dividend: Optional[float] = None
    total_dividend: Optional[float] = None
    dividend_yield: Optional[float] = None
    ex_dividend_date: Optional[date] = None


class DividendsResponse(BaseModel):
    """Dividend history for a stock."""

    stock_id: str
    stock_name: str
    dividends: list[DividendItem]
    avg_yield_5y: Optional[float] = None


class PeerComparisonItem(BaseModel):
    """Peer stock comparison data."""

    stock_id: str
    stock_name: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[float] = None


class PeersResponse(BaseModel):
    """Peer comparison response."""

    stock_id: str
    stock_name: str
    industry: Optional[str] = None
    peers: list[PeerComparisonItem]
    industry_pe_avg: Optional[float] = None
    industry_pb_avg: Optional[float] = None
    industry_roe_avg: Optional[float] = None
