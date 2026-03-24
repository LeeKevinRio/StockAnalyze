"""Text processing utilities for Chinese / stock-related content."""

import re
import unicodedata


def normalize_chinese(text: str) -> str:
    """Normalize full-width characters to half-width and strip whitespace.

    Converts characters like '\uff21' (A full-width) to 'A', '\uff10' (0 full-width)
    to '0', etc. Also collapses consecutive whitespace into a single space.

    Args:
        text: The input string to normalize.

    Returns:
        The normalized string with half-width characters and trimmed whitespace.
    """
    # NFKC normalization converts full-width to half-width equivalents
    normalized = unicodedata.normalize("NFKC", text)
    # Collapse consecutive whitespace and strip leading/trailing
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def title_similarity(a: str, b: str) -> float:
    """Compute a simple character overlap ratio between two strings.

    Uses the Dice coefficient on character sets for fast deduplication
    of news titles that may differ slightly between sources.

    Args:
        a: First string.
        b: Second string.

    Returns:
        A float between 0.0 and 1.0 representing the similarity.
        Returns 0.0 if both strings are empty.
    """
    if not a and not b:
        return 0.0

    set_a = set(a)
    set_b = set(b)

    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    return 2 * len(intersection) / (len(set_a) + len(set_b))


def extract_stock_ids(text: str) -> list[str]:
    """Extract 4-digit Taiwan stock IDs from text.

    Looks for standalone 4-digit numbers (not part of a longer number)
    that fall within the valid range for Taiwan stock IDs.

    Args:
        text: The text to search for stock IDs.

    Returns:
        A deduplicated list of matched stock ID strings, preserving order.
    """
    # Match 4-digit numbers that are not part of a longer digit sequence
    matches = re.findall(r"(?<!\d)(\d{4})(?!\d)", text)

    # Filter to plausible Taiwan stock ID ranges (1000-9999)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m not in seen and 1000 <= int(m) <= 9999:
            seen.add(m)
            result.append(m)

    return result
