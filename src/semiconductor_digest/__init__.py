"""semiconductor_digest: a daily semiconductor / design-verification news digest builder.

Fetches public RSS/Atom feeds, the arXiv API, and the Hacker News (Algolia)
API; dedupes against a persisted seen-URL cache; classifies items into
topic categories by keyword; and renders an HTML email plus a Markdown
archive entry. See ``semiconductor_digest.cli`` for the entry point and
``config/feeds.toml`` (repo root) for source/category configuration.
"""

from __future__ import annotations

__version__ = "0.1.0"
