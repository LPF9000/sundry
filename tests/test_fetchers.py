"""Fetcher tests run against mocked HTTP responses — no live network calls,
so the unit test suite stays fast and deterministic in CI. Live-source
verification happens separately via the PR-preview digest build."""

from unittest.mock import MagicMock

import pytest
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError

from tech_news_digest.fetchers.common import request_with_retries
from tech_news_digest.fetchers.hackernews import fetch_hn_query
from tech_news_digest.fetchers.rss import fetch_rss
from tech_news_digest.models import RssSource


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Retries add real backoff delay by design (see request_with_retries) --
    patched out here so the failure-path tests below don't slow down the
    suite waiting on sleeps that are irrelevant to what they're checking."""
    monkeypatch.setattr("tech_news_digest.fetchers.common.time.sleep", lambda _seconds: None)


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


def test_request_with_retries_succeeds_after_a_transient_failure(mock_session):
    ok_response = MagicMock(status_code=200)
    ok_response.raise_for_status.return_value = None
    mock_session.get.side_effect = [RequestsConnectionError("boom"), ok_response]

    response = request_with_retries(mock_session, "https://example.com", max_attempts=3, backoff_seconds=0)

    assert response is ok_response
    assert mock_session.get.call_count == 2


def test_request_with_retries_retries_a_5xx_response(mock_session):
    server_error = MagicMock(status_code=503)
    ok_response = MagicMock(status_code=200)
    ok_response.raise_for_status.return_value = None
    mock_session.get.side_effect = [server_error, ok_response]

    response = request_with_retries(mock_session, "https://example.com", max_attempts=3, backoff_seconds=0)

    assert response is ok_response
    assert mock_session.get.call_count == 2


def test_request_with_retries_does_not_retry_a_4xx_response(mock_session):
    forbidden = MagicMock(status_code=403)
    forbidden.raise_for_status.side_effect = requests.HTTPError("403 Client Error", response=forbidden)
    mock_session.get.return_value = forbidden

    with pytest.raises(requests.HTTPError):
        request_with_retries(mock_session, "https://example.com", max_attempts=3, backoff_seconds=0)

    assert mock_session.get.call_count == 1


def test_request_with_retries_raises_after_exhausting_attempts(mock_session):
    mock_session.get.side_effect = RequestsConnectionError("still down")

    with pytest.raises(RequestsConnectionError):
        request_with_retries(mock_session, "https://example.com", max_attempts=3, backoff_seconds=0)

    assert mock_session.get.call_count == 3


def test_fetch_rss_retries_a_transient_failure_then_succeeds(mock_session):
    ok_response = MagicMock(content=SAMPLE_RSS, status_code=200)
    ok_response.raise_for_status.return_value = None
    mock_session.get.side_effect = [RequestsConnectionError("boom"), ok_response]

    source = RssSource(name="Test Feed", url="https://example.com/feed")
    outcome = fetch_rss(source, mock_session)

    assert outcome.error is None
    assert len(outcome.articles) == 1
    assert mock_session.get.call_count == 2


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
