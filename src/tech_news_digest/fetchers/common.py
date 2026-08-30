"""Shared HTTP/parsing helpers and result type used by every fetcher."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..models import Article

USER_AGENT = "Mozilla/5.0 (compatible; tech-news-digest/1.0; +https://github.com/lpf9000/tech-news-digest)"
HTTP_TIMEOUT_SECONDS = 20


@dataclass(slots=True)
class FetchOutcome:
    """What came back from fetching one source: articles, or why it failed.

    A fetcher should never raise for an ordinary network/parse failure —
    it logs and returns an outcome with `error` set, so one dead source
    never aborts the run. `error` is a short human-readable reason, shown
    in the digest footer so failures stay visible without checking logs.
    """

    source_name: str
    articles: list[Article] = field(default_factory=list)
    error: str | None = None


def entry_datetime(entry: Any) -> datetime | None:
    """Best-effort UTC datetime from a feedparser entry's published/updated fields."""
    for attr in ("published_parsed", "updated_parsed"):
        value = getattr(entry, attr, None)
        if value:
            try:
                return datetime.fromtimestamp(calendar.timegm(value), tz=UTC)
            except (OverflowError, ValueError):
                continue
    return None
