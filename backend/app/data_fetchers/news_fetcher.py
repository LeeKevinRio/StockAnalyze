"""Fetcher for Taiwan stock news from multiple sources."""

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import feedparser
from bs4 import BeautifulSoup

from app.data_fetchers.base_fetcher import BaseFetcher
from app.utils.text_utils import normalize_chinese, title_similarity

logger = logging.getLogger(__name__)

# Source URLs
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
CNYES_API = "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock?limit=20"
YAHOO_TW_RSS = "https://tw.stock.yahoo.com/rss?s={stock_id}.TW"

# Similarity threshold for deduplication
DEDUP_THRESHOLD = 0.7


class NewsFetcher(BaseFetcher):
    """Aggregate Taiwan stock news from Google News, CNYES, and Yahoo Finance TW.

    Each source method returns a list of dicts with a uniform schema:
    ``{title, content, source, source_url, published_at}``.
    """

    def __init__(self) -> None:
        super().__init__(
            calls_per_minute=20,
            timeout=30.0,
            max_retries=3,
        )

    async def fetch(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Generic entry point — delegates to ``fetch_all_news``."""
        stock_id: str = kwargs.get("stock_id", "")
        stock_name: str = kwargs.get("stock_name", "")
        return await self.fetch_all_news(stock_id, stock_name)

    # ------------------------------------------------------------------
    # Google News
    # ------------------------------------------------------------------

    async def fetch_google_news(
        self, query: str, lang: str = "zh-TW"
    ) -> list[dict[str, Any]]:
        """Fetch news articles from Google News RSS feed.

        Args:
            query: Search query (e.g. stock name or ID).
            lang: Language code (default ``zh-TW``).

        Returns:
            List of article dicts.
        """
        url = GOOGLE_NEWS_RSS.format(query=quote(query))
        try:
            response = await self.get(url)
            feed = feedparser.parse(response.text)
        except Exception as exc:
            logger.error("Failed to fetch Google News for '%s': %s", query, exc)
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries:
            published_at = _parse_feed_date(entry.get("published"))
            articles.append(
                {
                    "title": normalize_chinese(entry.get("title", "")),
                    "content": _strip_html(entry.get("summary", "")),
                    "source": "google_news",
                    "source_url": entry.get("link", ""),
                    "published_at": published_at,
                }
            )

        logger.info(
            "Google News returned %d articles for '%s'", len(articles), query
        )
        return articles

    # ------------------------------------------------------------------
    # CNYES (鉅亨網)
    # ------------------------------------------------------------------

    async def fetch_cnyes_news(self, stock_id: str) -> list[dict[str, Any]]:
        """Fetch news from CNYES (鉅亨網) API.

        Args:
            stock_id: Taiwan stock ID (e.g. ``"2330"``).

        Returns:
            List of article dicts.
        """
        try:
            response = await self.get(
                CNYES_API,
                headers={"Accept": "application/json"},
            )
            data = response.json()
        except Exception as exc:
            logger.error("Failed to fetch CNYES news: %s", exc)
            return []

        items = (
            data.get("items", {}).get("data", [])
            if isinstance(data.get("items"), dict)
            else data.get("data", [])
        )

        articles: list[dict[str, Any]] = []
        for item in items:
            title = normalize_chinese(str(item.get("title", "")))
            # Optionally filter to articles mentioning the stock
            if stock_id and stock_id not in title:
                content = str(item.get("content", ""))
                if stock_id not in content:
                    continue

            published_ts = item.get("publishAt") or item.get("created_at")
            published_at: datetime | None = None
            if isinstance(published_ts, (int, float)):
                published_at = datetime.fromtimestamp(published_ts, tz=timezone.utc)

            news_id = item.get("newsId", "")
            articles.append(
                {
                    "title": title,
                    "content": _strip_html(str(item.get("content", ""))),
                    "source": "cnyes",
                    "source_url": f"https://news.cnyes.com/news/id/{news_id}" if news_id else "",
                    "published_at": published_at,
                }
            )

        logger.info(
            "CNYES returned %d articles for stock %s", len(articles), stock_id
        )
        return articles

    # ------------------------------------------------------------------
    # Yahoo Finance TW
    # ------------------------------------------------------------------

    async def fetch_yahoo_news(self, stock_id: str) -> list[dict[str, Any]]:
        """Fetch news from Yahoo Finance Taiwan RSS feed.

        Args:
            stock_id: Taiwan stock ID (e.g. ``"2330"``).

        Returns:
            List of article dicts.
        """
        url = YAHOO_TW_RSS.format(stock_id=stock_id)
        try:
            response = await self.get(url)
            feed = feedparser.parse(response.text)
        except Exception as exc:
            logger.error("Failed to fetch Yahoo TW news for %s: %s", stock_id, exc)
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries:
            published_at = _parse_feed_date(entry.get("published"))
            articles.append(
                {
                    "title": normalize_chinese(entry.get("title", "")),
                    "content": _strip_html(entry.get("summary", "")),
                    "source": "yahoo",
                    "source_url": entry.get("link", ""),
                    "published_at": published_at,
                }
            )

        logger.info(
            "Yahoo TW returned %d articles for stock %s", len(articles), stock_id
        )
        return articles

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    async def fetch_all_news(
        self, stock_id: str, stock_name: str
    ) -> list[dict[str, Any]]:
        """Fetch and deduplicate news from all configured sources.

        Uses the stock name (or ID) as the Google News query and fetches
        from CNYES and Yahoo in parallel.  Deduplication is based on
        title character similarity.

        Args:
            stock_id: Taiwan stock ID.
            stock_name: Human-readable stock name for search queries.

        Returns:
            Deduplicated list of article dicts sorted by published date.
        """
        import asyncio

        query = stock_name if stock_name else stock_id

        results = await asyncio.gather(
            self.fetch_google_news(query),
            self.fetch_cnyes_news(stock_id),
            self.fetch_yahoo_news(stock_id),
            return_exceptions=True,
        )

        all_articles: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("News source failed: %s", result)
                continue
            all_articles.extend(result)

        deduplicated = _deduplicate_articles(all_articles)
        # Sort by published_at descending (most recent first), nulls last
        deduplicated.sort(
            key=lambda a: a.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info(
            "Total news: %d raw -> %d after dedup for %s",
            len(all_articles),
            len(deduplicated),
            stock_id,
        )
        return deduplicated


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_feed_date(date_str: str | None) -> datetime | None:
    """Best-effort parsing of RSS date strings."""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    # Fallback: try common ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _strip_html(html: str) -> str:
    """Remove HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _deduplicate_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove near-duplicate articles based on title similarity."""
    unique: list[dict[str, Any]] = []
    for article in articles:
        title = article.get("title", "")
        is_dup = any(
            title_similarity(title, existing.get("title", "")) >= DEDUP_THRESHOLD
            for existing in unique
        )
        if not is_dup:
            unique.append(article)
    return unique
