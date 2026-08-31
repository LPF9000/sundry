"""tech_news_digest: a reusable, config-driven daily news digest builder.

Fetches public RSS/Atom feeds, the arXiv API, and the Hacker News (Algolia)
API; dedupes against a persisted seen-URL cache; classifies items into
topic categories by keyword; and renders an HTML email plus a Markdown
archive entry. See ``tech_news_digest.cli`` for the entry point and
``examples/feeds.toml`` for an annotated example of the source/category
configuration this reads — nothing in this package is topic-specific,
and this repo ships no default topic. Run ``tech-news-digest init`` in
your own repo to scaffold one, or see
https://github.com/LPF9000/semiconductor-news-digest for a complete
real-world example.
"""

from __future__ import annotations

__version__ = "1.0.0"
