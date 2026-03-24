"""FRED (Federal Reserve Economic Data) API fetcher.

Retrieves macro economic indicators from the FRED API including
Federal Funds Rate, 10-Year Treasury yield, VIX, and exchange rates.

API documentation: https://fred.stlouisfed.org/docs/api/fred/
Rate limit: 120 requests per minute per API key.
"""

import logging
from datetime import date, timedelta
from typing import Any, Optional

from app.config import settings
from app.data_fetchers.base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)


# Well-known FRED series IDs for macro indicators
SERIES_FEDFUNDS = "FEDFUNDS"       # Federal Funds Effective Rate
SERIES_DGS10 = "DGS10"             # 10-Year Treasury Constant Maturity Rate
SERIES_VIXCLS = "VIXCLS"           # CBOE Volatility Index: VIX
SERIES_DEXTWUS = "DEXTWUS"         # Taiwan Dollar to US Dollar Exchange Rate

# Display names for common series
SERIES_NAMES = {
    SERIES_FEDFUNDS: "聯邦基金利率",
    SERIES_DGS10: "美國10年期公債殖利率",
    SERIES_VIXCLS: "VIX 恐慌指數",
    SERIES_DEXTWUS: "台幣/美元匯率",
}

_FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FREDFetcher(BaseFetcher):
    """Fetch macro economic data from the FRED API.

    Handles missing FRED_API_KEY gracefully by returning empty data.
    Uses the BaseFetcher retry and rate-limiting infrastructure.
    """

    def __init__(self) -> None:
        super().__init__(
            calls_per_minute=100,  # Stay well under the 120/min limit
            timeout=15.0,
            max_retries=2,
        )
        self._api_key = settings.FRED_API_KEY

    @property
    def is_available(self) -> bool:
        """Whether the FRED API key is configured."""
        return bool(self._api_key)

    async def fetch(self, **kwargs: Any) -> Any:
        """Generic fetch interface (required by BaseFetcher).

        Delegates to fetch_indicator for the specified series_id.
        """
        series_id = kwargs.get("series_id", "")
        if not series_id:
            return None
        return await self.fetch_indicator(series_id)

    async def fetch_indicator(
        self,
        series_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[dict]:
        """Fetch a single FRED indicator series.

        Args:
            series_id: FRED series identifier (e.g. 'FEDFUNDS', 'DGS10').
            start_date: Start date for observations. Defaults to 90 days ago.
            end_date: End date for observations. Defaults to today.

        Returns:
            Dict with value, previous_value, change, trend, and updated_at.
            Returns None if the API key is missing or the request fails.
        """
        if not self.is_available:
            logger.debug("FRED API key not configured; skipping %s", series_id)
            return None

        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=90)

        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "observation_start": start_date.isoformat(),
            "observation_end": end_date.isoformat(),
            "sort_order": "desc",
            "limit": "10",
        }

        try:
            response = await self.get(_FRED_BASE_URL, params=params)
            data = response.json()

            observations = data.get("observations", [])
            if not observations:
                logger.info("No observations returned for FRED series %s", series_id)
                return None

            return self._parse_observations(series_id, observations)

        except Exception as exc:
            logger.warning("Failed to fetch FRED series %s: %s", series_id, exc)
            return None

    async def fetch_multiple(
        self,
        series_ids: list[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, Optional[dict]]:
        """Fetch multiple FRED series.

        Fetches each series sequentially to respect rate limits.

        Args:
            series_ids: List of FRED series identifiers.
            start_date: Start date for observations.
            end_date: End date for observations.

        Returns:
            Dict mapping series_id to indicator dict (or None on failure).
        """
        results = {}
        for series_id in series_ids:
            results[series_id] = await self.fetch_indicator(
                series_id, start_date, end_date
            )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_observations(series_id: str, observations: list[dict]) -> Optional[dict]:
        """Parse FRED observations into a structured indicator dict.

        Takes the most recent non-missing observations and computes
        change and trend information.

        Args:
            series_id: The FRED series identifier.
            observations: List of observation dicts from FRED API (sorted desc).

        Returns:
            Structured dict with value, previous_value, change, trend, updated_at.
        """
        # Filter out missing values ("." means no data in FRED)
        valid_obs = []
        for obs in observations:
            val_str = obs.get("value", "").strip()
            if val_str and val_str != ".":
                try:
                    valid_obs.append({
                        "value": float(val_str),
                        "date": obs.get("date", ""),
                    })
                except ValueError:
                    continue

        if not valid_obs:
            return None

        current = valid_obs[0]
        current_value = current["value"]
        updated_at = current["date"]

        # Find previous value for comparison
        previous_value = None
        change = None
        trend = "stable"

        if len(valid_obs) >= 2:
            previous_value = valid_obs[1]["value"]
            change = round(current_value - previous_value, 4)

            if change > 0.01:
                trend = "rising"
            elif change < -0.01:
                trend = "falling"
            else:
                trend = "stable"

        return {
            "series_id": series_id,
            "name": SERIES_NAMES.get(series_id, series_id),
            "value": current_value,
            "previous_value": previous_value,
            "change": change,
            "trend": trend,
            "updated_at": updated_at,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

fred_fetcher = FREDFetcher()
