"""Fetcher for Taiwan Stock Exchange (TWSE) Open API data."""

import logging
from typing import Any

from app.data_fetchers.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

# TWSE Open API endpoints
TWSE_STOCK_DAY_ALL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TWSE_STOCK_INFO = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"


class TWSEFetcher(BaseFetcher):
    """Fetch stock data from the Taiwan Stock Exchange Open API.

    TWSE rate-limits aggressively, so we default to a conservative
    5 calls per minute to avoid being blocked.
    """

    def __init__(self) -> None:
        super().__init__(
            calls_per_minute=5,
            timeout=30.0,
            max_retries=3,
        )

    async def fetch(self, **kwargs: Any) -> Any:
        """Generic entry point — delegates to ``fetch_stock_list``."""
        return await self.fetch_stock_list()

    async def fetch_stock_list(self) -> list[dict[str, str]]:
        """Fetch the full list of listed stocks from TWSE.

        Returns a list of dicts, each containing basic stock information
        sourced from the ``STOCK_DAY_ALL`` endpoint.  TWSE returns fields
        with Chinese names; this method maps them to English keys.

        Returns:
            List of dicts with keys: stock_id, name, volume, open,
            high, low, close, change, trade_count.
        """
        response = await self.get(TWSE_STOCK_DAY_ALL)
        raw_items: list[dict[str, str]] = response.json()

        stocks: list[dict[str, str]] = []
        for item in raw_items:
            try:
                stocks.append(
                    {
                        "stock_id": item.get("Code", "").strip(),
                        "name": item.get("Name", "").strip(),
                        "volume": item.get("TradeVolume", "0"),
                        "open": item.get("OpeningPrice", "0"),
                        "high": item.get("HighestPrice", "0"),
                        "low": item.get("LowestPrice", "0"),
                        "close": item.get("ClosingPrice", "0"),
                        "change": item.get("Change", "0"),
                        "trade_count": item.get("Transaction", "0"),
                    }
                )
            except Exception:
                logger.warning("Failed to parse TWSE stock item: %s", item)
                continue

        logger.info("Fetched %d stocks from TWSE STOCK_DAY_ALL", len(stocks))
        return stocks

    async def fetch_daily_prices(self, date_str: str) -> list[dict[str, str]]:
        """Fetch daily OHLCV data for all stocks on a given date.

        The ``STOCK_DAY_ALL`` endpoint returns the latest trading day data
        regardless of the ``date_str`` parameter (TWSE Open API limitation).
        The ``date_str`` is kept in the signature for future compatibility
        with date-specific APIs.

        Args:
            date_str: Target date in ``YYYYMMDD`` format (informational).

        Returns:
            List of dicts with OHLCV keys per stock.
        """
        logger.info("Fetching daily prices for date: %s", date_str)
        response = await self.get(TWSE_STOCK_DAY_ALL)
        raw_items: list[dict[str, str]] = response.json()

        prices: list[dict[str, str]] = []
        for item in raw_items:
            try:
                stock_id = item.get("Code", "").strip()
                if not stock_id:
                    continue
                prices.append(
                    {
                        "stock_id": stock_id,
                        "name": item.get("Name", "").strip(),
                        "volume": item.get("TradeVolume", "0"),
                        "trade_value": item.get("TradeValue", "0"),
                        "open": item.get("OpeningPrice", "0"),
                        "high": item.get("HighestPrice", "0"),
                        "low": item.get("LowestPrice", "0"),
                        "close": item.get("ClosingPrice", "0"),
                        "change": item.get("Change", "0"),
                        "trade_count": item.get("Transaction", "0"),
                    }
                )
            except Exception:
                logger.warning("Failed to parse TWSE price item: %s", item)
                continue

        logger.info("Fetched daily prices for %d stocks", len(prices))
        return prices

    async def fetch_stock_info(self) -> list[dict[str, str]]:
        """Fetch basic stock information from the TWSE open-data endpoint.

        Returns a list of dicts with company information including
        stock ID, name, industry, and listing date.

        Returns:
            List of dicts with keys: stock_id, name, isin_code, listed_date,
            market, industry, cfi_code.
        """
        response = await self.get(TWSE_STOCK_INFO)
        raw_items: list[dict[str, str]] = response.json()

        info_list: list[dict[str, str]] = []
        for item in raw_items:
            try:
                info_list.append(
                    {
                        "stock_id": item.get("公司代號", "").strip(),
                        "name": item.get("公司簡稱", "").strip(),
                        "isin_code": item.get("國際證券辨識號碼", "").strip(),
                        "listed_date": item.get("上市日", "").strip(),
                        "market": "TWSE",
                        "industry": item.get("產業別", "").strip(),
                        "cfi_code": item.get("CFICode", "").strip(),
                    }
                )
            except Exception:
                logger.warning("Failed to parse TWSE info item: %s", item)
                continue

        logger.info("Fetched info for %d stocks from TWSE", len(info_list))
        return info_list
