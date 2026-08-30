"""Load and validate ``config/feeds.toml`` into a typed `DigestConfig`.

Parsed with the standard-library `tomllib` (Python 3.11+) — no third-party
dependency needed just to read configuration.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .models import ArxivSource, Category, DigestConfig, RssSource

# repo_root/src/semiconductor_digest/config.py -> repo_root/config/feeds.toml
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "feeds.toml"


class ConfigError(ValueError):
    """Raised when feeds.toml is missing required fields or is inconsistent."""


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> DigestConfig:
    """Parse and validate the TOML source/category configuration at `path`."""
    path = Path(path)
    with path.open("rb") as f:
        raw: dict[str, Any] = tomllib.load(f)

    categories = _parse_categories(raw.get("categories") or [], path)
    category_keys = {category.key for category in categories}

    rss_sources = tuple(
        RssSource(name=s["name"], url=s["url"], default_category=s.get("default_category"))
        for s in raw.get("rss_sources") or []
    )
    for source in rss_sources:
        if source.default_category and source.default_category not in category_keys:
            raise ConfigError(
                f"{path}: {source.name!r} default_category {source.default_category!r} is not a defined category key"
            )

    arxiv_sources = tuple(
        ArxivSource(name=s["name"], query=s["query"], max_results=int(s.get("max_results", 20)))
        for s in raw.get("arxiv_sources") or []
    )
    hn_queries = tuple(raw.get("hn_queries") or [])

    return DigestConfig(
        rss_sources=rss_sources,
        arxiv_sources=arxiv_sources,
        hn_queries=hn_queries,
        categories=categories,
    )


def _parse_categories(raw_categories: list[dict[str, Any]], path: Path) -> tuple[Category, ...]:
    categories = tuple(
        Category(
            key=c["key"],
            title=c["title"],
            blurb=(c.get("blurb") or "").strip(),
            keywords=tuple(keyword.lower() for keyword in c.get("keywords") or []),
            max_items=int(c.get("max_items", 8)),
        )
        for c in raw_categories
    )
    if not categories:
        raise ConfigError(f"{path}: no categories defined")

    keys = [category.key for category in categories]
    if len(keys) != len(set(keys)):
        raise ConfigError(f"{path}: duplicate category keys: {keys}")
    if "general" not in keys:
        raise ConfigError(f"{path}: a 'general' catch-all category is required")

    return categories
