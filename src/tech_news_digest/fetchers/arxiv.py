"""arXiv API fetching — public, no key needed. The API returns Atom, so we
reuse `feedparser` for parsing just like the RSS fetcher."""

from __future__ import annotations

import logging
import time
from urllib.parse import quote

import feedparser
import requests

from ..models import Article, ArxivSource
from ..text import strip_html, truncate
from .common import HTTP_TIMEOUT_SECONDS, FetchOutcome, entry_datetime

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
# arXiv's API terms of use ask for a short pause between consecutive requests.
COURTESY_DELAY_SECONDS = 3.0


def fetch_arxiv(source: ArxivSource, session: requests.Session, *, delay: bool = True) -> FetchOutcome:
    """Run one saved arXiv search, sorted newest-submitted-first."""
    url = (
        f"{ARXIV_API_URL}?search_query={quote(source.query)}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={source.max_results}"
    )
    try:
        response = session.get(url, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("arXiv fetch failed for %s: %s", source.name, exc)
        return FetchOutcome(source.name, error=exc.__class__.__name__)
    finally:
        if delay:
            time.sleep(COURTESY_DELAY_SECONDS)

    parsed = feedparser.parse(response.content)
    articles = []
    for entry in parsed.entries:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue
        authors = ", ".join(author.get("name", "") for author in getattr(entry, "authors", []) if author.get("name"))
        summary = strip_html(getattr(entry, "summary", ""))
        if authors:
            summary = f"{authors} — {summary}"
        articles.append(
            Article(
                title=strip_html(title).replace("\n", " "),
                link=link,
                summary=truncate(summary),
                source=source.name,
                published=entry_datetime(entry),
            )
        )
    return FetchOutcome(source.name, articles=articles)
