"""Typed data models shared across the digest pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Article:
    """A single news/paper/post item pulled from a source, ready to classify."""

    title: str
    link: str
    summary: str
    source: str
    published: datetime | None = None
    forced_category: str | None = None
    """Category key this article must be filed under, bypassing keyword
    scoring — set by sources that are already 100% on-topic (e.g. a pure
    cryptography research feed should always land in crypto_security)."""


@dataclass(frozen=True, slots=True)
class Category:
    """One topic bucket in the digest, and the rules used to fill it."""

    key: str
    title: str
    blurb: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    max_items: int = 8


@dataclass(frozen=True, slots=True)
class RssSource:
    """A plain RSS/Atom feed to poll."""

    name: str
    url: str
    default_category: str | None = None


@dataclass(frozen=True, slots=True)
class ArxivSource:
    """A saved search against the public arXiv API."""

    name: str
    query: str
    max_results: int = 20


@dataclass(frozen=True, slots=True)
class DigestConfig:
    """Everything loaded from ``config/feeds.toml``."""

    rss_sources: tuple[RssSource, ...]
    arxiv_sources: tuple[ArxivSource, ...]
    hn_queries: tuple[str, ...]
    categories: tuple[Category, ...]

    def category_by_key(self) -> dict[str, Category]:
        return {category.key: category for category in self.categories}
