"""Fetcher tests run against mocked HTTP responses — no live network calls,
so the unit test suite stays fast and deterministic in CI. Live-source
verification happens separately via the PR-preview digest build."""

from unittest.mock import MagicMock

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError

from semiconductor_digest.fetchers.hackernews import fetch_hn_query
from semiconductor_digest.fetchers.rss import fetch_rss
from semiconductor_digest.models import RssSource

SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Feed</title>
<item>
  <title>UVM testbench improves coverage closure</title>
  <link>https://example.com/article</link>
  <description>&lt;p&gt;A short summary.&lt;/p&gt;</description>
  <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
</item>
</channel></rss>
"""


@pytest.fixture
def mock_session():
    return MagicMock()


def test_fetch_rss_parses_entries(mock_session):
    mock_session.get.return_value = MagicMock(content=SAMPLE_RSS, status_code=200)
    mock_session.get.return_value.raise_for_status.return_value = None

    source = RssSource(name="Test Feed", url="https://example.com/feed")
    outcome = fetch_rss(source, mock_session)

    assert outcome.error is None
    assert len(outcome.articles) == 1
    article = outcome.articles[0]
    assert article.title == "UVM testbench improves coverage closure"
    assert article.link == "https://example.com/article"
    assert article.summary == "A short summary."
    assert article.source == "Test Feed"


def test_fetch_rss_forces_the_configured_category(mock_session):
    mock_session.get.return_value = MagicMock(content=SAMPLE_RSS, status_code=200)
    mock_session.get.return_value.raise_for_status.return_value = None

    source = RssSource(name="Test Feed", url="https://example.com/feed", default_category="crypto_security")
    outcome = fetch_rss(source, mock_session)

    assert outcome.articles[0].forced_category == "crypto_security"


def test_fetch_rss_handles_request_failure_gracefully(mock_session):
    mock_session.get.side_effect = RequestsConnectionError("boom")

    source = RssSource(name="Down Feed", url="https://example.com/feed")
    outcome = fetch_rss(source, mock_session)

    assert outcome.articles == []
    assert outcome.error is not None


def test_fetch_hn_query_filters_low_point_stories(mock_session):
    mock_session.get.return_value = MagicMock(status_code=200)
    mock_session.get.return_value.raise_for_status.return_value = None
    mock_session.get.return_value.json.return_value = {
        "hits": [
            {"title": "Big RISC-V story", "url": "https://example.com/big", "points": 50, "objectID": "1"},
            {"title": "Tiny story", "url": "https://example.com/tiny", "points": 1, "objectID": "2"},
        ]
    }

    outcome = fetch_hn_query("RISC-V", mock_session)

    assert outcome.error is None
    assert [article.link for article in outcome.articles] == ["https://example.com/big"]
