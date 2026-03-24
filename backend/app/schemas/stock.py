"""Stock-related Pydantic schemas."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockResponse(BaseModel):
    stock_id: str
    name: str
    english_name: Optional[str] = None
    industry: Optional[str] = None
    market: str

    model_config = {"from_attributes": True}


class StockPriceResponse(BaseModel):
    stock_id: str
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[int] = None
    change_percent: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class StockDetailResponse(BaseModel):
    stock: StockResponse
    latest_price: Optional[StockPriceResponse] = None
    price_change: Optional[Decimal] = None
    price_change_percent: Optional[Decimal] = None


class StockSearchResult(BaseModel):
    stock_id: str
    name: str
    industry: Optional[str] = None
    market: str

    model_config = {"from_attributes": True}
