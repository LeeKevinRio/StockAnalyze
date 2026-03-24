"""Date and time utilities for Taiwan timezone operations."""

from datetime import date, datetime, timedelta, timezone

# Taiwan timezone: UTC+8
TW_TZ = timezone(timedelta(hours=8))


def get_tw_now() -> datetime:
    """Return the current datetime in Taiwan timezone (UTC+8)."""
    return datetime.now(TW_TZ)


def get_tw_today() -> date:
    """Return today's date in Taiwan timezone (UTC+8)."""
    return get_tw_now().date()


def is_trading_day(d: date) -> bool:
    """Check whether a given date is a trading day.

    Currently excludes weekends only. Holiday exclusions can be added later
    by maintaining a list of known Taiwan stock market holidays.

    Args:
        d: The date to check.

    Returns:
        True if the date falls on a weekday (Monday-Friday).
    """
    return d.weekday() < 5  # 0=Monday ... 4=Friday


def get_last_trading_day() -> date:
    """Return the most recent trading day relative to the current Taiwan time.

    If today is a trading day and the market has closed (after 13:30 TW),
    today is returned. Otherwise the previous trading day is returned.
    """
    now = get_tw_now()
    today = now.date()

    # Market closes at 13:30 TW time
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)

    if is_trading_day(today) and now >= market_close:
        return today

    # Walk backwards to find the last trading day
    candidate = today - timedelta(days=1)
    while not is_trading_day(candidate):
        candidate -= timedelta(days=1)

    return candidate
