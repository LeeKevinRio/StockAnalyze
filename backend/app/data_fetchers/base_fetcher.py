"""Abstract base class for all data fetchers with retry, rate-limiting, and timeout."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Base class providing retry logic, rate limiting, and timeout handling.

    Subclasses must implement the ``fetch`` method with their specific
    data retrieval logic.

    Args:
        calls_per_minute: Maximum number of HTTP calls allowed per minute.
        timeout: Default request timeout in seconds.
        max_retries: Maximum number of retry attempts for transient failures.
    """

    def __init__(
        self,
        calls_per_minute: int = 30,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.calls_per_minute = calls_per_minute
        self.timeout = timeout
        self.max_retries = max_retries

        # Rate-limiting state
        self._min_interval = 60.0 / calls_per_minute
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    async def _wait_for_rate_limit(self) -> None:
        """Block until enough time has elapsed to respect the rate limit."""
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Target URL.
            headers: Optional request headers.
            params: Optional query parameters.
            cookies: Optional request cookies.

        Returns:
            The ``httpx.Response`` object on success.

        Raises:
            httpx.HTTPStatusError: If the request fails after all retries.
            httpx.TimeoutException: If every attempt times out.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            await self._wait_for_rate_limit()

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        cookies=cookies,
                    )
                    response.raise_for_status()
                    return response

            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "Timeout on attempt %d/%d for %s: %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status = exc.response.status_code
                # Do not retry client errors other than 429 (Too Many Requests)
                if 400 <= status < 500 and status != 429:
                    logger.error(
                        "Client error %d for %s — not retrying: %s",
                        status,
                        url,
                        exc,
                    )
                    raise
                logger.warning(
                    "HTTP %d on attempt %d/%d for %s",
                    status,
                    attempt,
                    self.max_retries,
                    url,
                )
            except httpx.RequestError as exc:
                last_exception = exc
                logger.warning(
                    "Request error on attempt %d/%d for %s: %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )

            # Exponential backoff: 1s, 2s, 4s, ...
            if attempt < self.max_retries:
                backoff = 2 ** (attempt - 1)
                logger.info("Retrying in %ds ...", backoff)
                await asyncio.sleep(backoff)

        # All retries exhausted
        logger.error(
            "All %d attempts failed for %s", self.max_retries, url
        )
        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"All {self.max_retries} attempts failed for {url}")

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Convenience wrapper for HTTP GET with retry and rate limiting."""
        return await self._request(
            "GET", url, headers=headers, params=params, cookies=cookies
        )

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> Any:
        """Fetch data from the external source.

        Subclasses must implement this with their specific retrieval logic.
        """
        ...
