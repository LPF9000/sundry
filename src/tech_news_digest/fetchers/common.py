"""Shared HTTP/parsing helpers and result type used by every fetcher."""

from __future__ import annotations

import calendar
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import requests

from ..models import Article

USER_AGENT = "Mozilla/5.0 (compatible; tech-news-digest/1.0; +https://github.com/lpf9000/tech-news-digest)"
HTTP_TIMEOUT_SECONDS = 20
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0


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


def request_with_retries(
    session: requests.Session,
    url: str,
    *,
    timeout: float = HTTP_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    **kwargs: Any,
) -> requests.Response:
    """GET `url`, retrying transient failures up to `max_attempts` times
    with a short linear backoff between attempts.

    A daily unattended run has no one around to retry a source that
    dropped a single connection or hiccuped with a 503 — this absorbs
    exactly that class of failure. A 4xx response is never retried: a bad
    request, a 403 block, or a 404 won't succeed on a second try, so
    failing fast there keeps one truly-broken source from adding retry
    delay for no benefit. Raises the last error if every attempt fails.
    """
    last_exc: requests.RequestException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            if response.status_code < 500:
                response.raise_for_status()  # only 4xx can raise here; never retried
                return response
            last_exc = requests.HTTPError(f"{response.status_code} server error", response=response)
        if attempt < max_attempts:
            time.sleep(backoff_seconds * attempt)
    assert last_exc is not None  # the loop always sets this before falling through
    raise last_exc


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
