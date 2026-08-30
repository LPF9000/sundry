"""tech_news_digest: a reusable, config-driven daily news digest builder.

Fetches public RSS/Atom feeds, the arXiv API, and the Hacker News (Algolia)
API; dedupes against a persisted seen-URL cache; classifies items into
topic categories by keyword; and renders an HTML email plus a Markdown
archive entry. See ``tech_news_digest.cli`` for the entry point and
``config/feeds.toml`` (repo root) for source/category configuration — this
repo ships pre-configured for semiconductor/design-verification news, but
nothing in this package is topic-specific; repoint the config for any topic.
"""

from __future__ import annotations

__version__ = "0.2.0"
