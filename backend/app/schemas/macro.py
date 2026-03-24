"""Macro economic analysis Pydantic schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MacroIndicatorItem(BaseModel):
    """A single macro economic indicator."""

    name: str
    value: Optional[float] = None
    previous_value: Optional[float] = None
    change: Optional[float] = None
    trend: Optional[str] = None  # "rising", "falling", "stable"
    updated_at: Optional[str] = None


class MacroDashboardResponse(BaseModel):
    """Full macro economic dashboard."""

    interest_rate: Optional[MacroIndicatorItem] = None
    taiwan_rate: Optional[MacroIndicatorItem] = None
    exchange_rate: Optional[MacroIndicatorItem] = None  # TWD/USD
    taiex: Optional[MacroIndicatorItem] = None
    vix: Optional[MacroIndicatorItem] = None
    ten_year_treasury: Optional[MacroIndicatorItem] = None

    business_cycle: Optional[str] = None  # "expansion", "contraction", "recovery", "slowdown"
    rate_cycle: Optional[str] = None  # "cutting", "hiking", "holding"

    score: float = 0.0
    summary: Optional[str] = None
    updated_at: Optional[str] = None


class MacroIndicatorsResponse(BaseModel):
    """Raw macro indicator data."""

    indicators: list[MacroIndicatorItem]
    updated_at: Optional[str] = None
