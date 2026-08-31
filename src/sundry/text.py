"""Small text-cleanup helpers shared by every fetcher and renderer."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

DEFAULT_SUMMARY_LIMIT = 240


def strip_html(text: str | None) -> str:
    """Remove HTML tags and unescape entities, collapsing whitespace."""
    if not text:
        return ""
    without_tags = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", html.unescape(without_tags)).strip()


def truncate(text: str, limit: int = DEFAULT_SUMMARY_LIMIT) -> str:
    """Shorten `text` to `limit` chars on a word boundary, adding an ellipsis."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"
