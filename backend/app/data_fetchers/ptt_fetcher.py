"""Scraper for PTT Stock board (批踢踢股票版)."""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.data_fetchers.base_fetcher import BaseFetcher
from app.utils.text_utils import normalize_chinese

logger = logging.getLogger(__name__)

PTT_BASE = "https://www.ptt.cc"
PTT_STOCK_INDEX = f"{PTT_BASE}/bbs/Stock/index.html"
PTT_COOKIES = {"over18": "1"}


class PTTFetcher(BaseFetcher):
    """Scrape the PTT Stock board for recent posts and content.

    PTT requires the ``over18=1`` cookie to bypass the age gate.
    We use conservative rate limiting (10 calls/min) to avoid being
    blocked.
    """

    def __init__(self) -> None:
        super().__init__(
            calls_per_minute=10,
            timeout=30.0,
            max_retries=3,
        )

    async def fetch(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Generic entry point — delegates to ``fetch_recent_posts``."""
        pages: int = kwargs.get("pages", 3)
        return await self.fetch_recent_posts(pages=pages)

    async def fetch_recent_posts(
        self, pages: int = 3
    ) -> list[dict[str, Any]]:
        """Fetch recent post summaries from the PTT Stock board.

        Iterates backwards through ``pages`` index pages starting from
        the latest, parsing each post's title, author, date, and
        push/boo counts.

        Args:
            pages: Number of index pages to scrape (default 3).

        Returns:
            List of post summary dicts.
        """
        all_posts: list[dict[str, Any]] = []
        current_url = PTT_STOCK_INDEX

        for page_num in range(pages):
            try:
                response = await self.get(current_url, cookies=PTT_COOKIES)
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as exc:
                logger.error(
                    "Failed to fetch PTT page %d (%s): %s",
                    page_num + 1,
                    current_url,
                    exc,
                )
                break

            posts = _parse_index_page(soup)
            all_posts.extend(posts)

            # Find "上頁" (previous page) link
            prev_link = _find_prev_page_link(soup)
            if prev_link:
                current_url = f"{PTT_BASE}{prev_link}"
            else:
                break

        logger.info("Fetched %d posts from %d PTT pages", len(all_posts), pages)
        return all_posts

    async def fetch_post_content(self, url: str) -> str:
        """Fetch the full text content of a single PTT post.

        Args:
            url: Absolute URL of the PTT post.

        Returns:
            The post's main body text, stripped of HTML.
        """
        try:
            response = await self.get(url, cookies=PTT_COOKIES)
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as exc:
            logger.error("Failed to fetch PTT post %s: %s", url, exc)
            return ""

        # Main content sits inside <div id="main-content">
        main = soup.find("div", id="main-content")
        if not main:
            return ""

        # Remove metadata header lines (author, title, time, board)
        for meta in main.find_all("div", class_="article-metaline"):
            meta.decompose()
        for meta in main.find_all("div", class_="article-metaline-right"):
            meta.decompose()

        # Remove push (推/噓) section
        for push in main.find_all("div", class_="push"):
            push.decompose()

        return main.get_text(separator="\n", strip=True)

    def extract_mentioned_stocks(
        self,
        title: str,
        content: str,
        stock_list: dict[str, str],
    ) -> list[str]:
        """Extract stock IDs mentioned in a post title or body.

        Matches 4-digit stock IDs and known stock names against the
        provided ``stock_list`` mapping.

        Args:
            title: Post title.
            content: Post body text.
            stock_list: Mapping of ``{stock_id: stock_name}`` for all
                known stocks.

        Returns:
            Deduplicated list of matched stock IDs.
        """
        combined = f"{title} {content}"
        combined = normalize_chinese(combined)

        found: set[str] = set()

        # Match explicit 4-digit IDs
        for match in re.findall(r"(?<!\d)(\d{4})(?!\d)", combined):
            if match in stock_list:
                found.add(match)

        # Match stock names
        for stock_id, name in stock_list.items():
            if name and name in combined:
                found.add(stock_id)

        return sorted(found)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_index_page(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Parse a PTT board index page into a list of post summaries."""
    posts: list[dict[str, Any]] = []
    entries = soup.find_all("div", class_="r-ent")

    for entry in entries:
        try:
            # Title and link
            title_tag = entry.find("div", class_="title")
            if not title_tag:
                continue
            a_tag = title_tag.find("a")
            if not a_tag:
                # Post was deleted
                continue

            title = normalize_chinese(a_tag.get_text(strip=True))
            href = a_tag.get("href", "")
            url = f"{PTT_BASE}{href}" if href else ""

            # Author
            author_tag = entry.find("div", class_="author")
            author = author_tag.get_text(strip=True) if author_tag else ""

            # Date
            date_tag = entry.find("div", class_="date")
            date_str = date_tag.get_text(strip=True) if date_tag else ""

            # Push count (推/噓)
            push_count, boo_count = _parse_nrec(entry)

            posts.append(
                {
                    "platform": "ptt",
                    "board": "Stock",
                    "title": title,
                    "content": "",  # Filled later via fetch_post_content
                    "author": author,
                    "url": url,
                    "push_count": push_count,
                    "boo_count": boo_count,
                    "posted_at": _parse_ptt_date(date_str),
                    "mentioned_stocks": [],
                }
            )
        except Exception:
            logger.debug("Failed to parse PTT entry", exc_info=True)
            continue

    return posts


def _parse_nrec(entry: Any) -> tuple[int, int]:
    """Parse the push/boo count from a PTT entry's nrec div.

    PTT shows one of:
    - A number (net positive pushes)
    - 'X' followed by a number (net negative / boo-heavy)
    - '爆' (extremely popular)
    - Empty (no pushes)

    We approximate push and boo counts from this single value.
    """
    nrec_tag = entry.find("div", class_="nrec")
    if not nrec_tag:
        return 0, 0

    text = nrec_tag.get_text(strip=True)
    if not text:
        return 0, 0

    if text == "爆":
        return 100, 0

    if text.startswith("X"):
        digits = text[1:]
        try:
            return 0, int(digits) if digits else 1
        except ValueError:
            return 0, 1

    try:
        count = int(text)
        if count >= 0:
            return count, 0
        return 0, abs(count)
    except ValueError:
        return 0, 0


def _parse_ptt_date(date_str: str) -> datetime | None:
    """Parse PTT's short date format (e.g. ``' 3/24'`` or ``'12/05'``)."""
    date_str = date_str.strip()
    if not date_str:
        return None

    try:
        now = datetime.now(timezone.utc)
        month, day = date_str.split("/")
        return now.replace(
            month=int(month),
            day=int(day),
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    except (ValueError, AttributeError):
        return None


def _find_prev_page_link(soup: BeautifulSoup) -> str | None:
    """Find the link to the previous page on a PTT index page."""
    action_bar = soup.find("div", class_="btn-group-paging")
    if not action_bar:
        return None

    links = action_bar.find_all("a")
    for link in links:
        if "上頁" in link.get_text():
            return link.get("href")

    return None
