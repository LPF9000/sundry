from datetime import UTC, datetime

from sundry.models import Article, Category
from sundry.render import render_html, render_markdown

CATEGORIES = (
    Category(key="dv_uvm", title="DV & UVM", blurb="Testbenches etc.", keywords=(), max_items=8),
    Category(key="general", title="General", blurb="Catch-all.", keywords=(), max_items=5),
)


def _article(title="Title", link="https://example.com/a", summary="A summary."):
    return Article(
        title=title,
        link=link,
        summary=summary,
        source="Src",
        published=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_render_html_escapes_untrusted_title():
    categorized = {"dv_uvm": [_article(title="<script>alert(1)</script>")], "general": []}
    out = render_html("2026-01-01", categorized, CATEGORIES, [])
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def test_render_html_notes_a_quiet_day():
    out = render_html("2026-01-01", {"dv_uvm": [], "general": []}, CATEGORIES, [])
    assert "Quiet day" in out


def test_render_markdown_includes_link_and_summary():
    categorized = {"dv_uvm": [_article()], "general": []}
    out = render_markdown("2026-01-01", categorized, CATEGORIES, [])
    assert "[Title](https://example.com/a)" in out
    assert "A summary." in out


def test_render_notes_source_failures_in_both_formats():
    empty = {"dv_uvm": [], "general": []}
    failures = ["Some Source (Timeout)"]

    assert "Some Source (Timeout)" in render_html("2026-01-01", empty, CATEGORIES, failures)
    assert "Some Source (Timeout)" in render_markdown("2026-01-01", empty, CATEGORIES, failures)


def test_empty_categories_are_omitted_from_output():
    categorized = {"dv_uvm": [], "general": [_article(title="General item")]}
    out = render_markdown("2026-01-01", categorized, CATEGORIES, [])
    assert "DV & UVM" not in out
    assert "General item" in out


def test_digest_name_defaults_to_generic_title():
    empty = {"dv_uvm": [], "general": []}
    assert "Daily Digest" in render_html("2026-01-01", empty, CATEGORIES, [])
    assert render_markdown("2026-01-01", empty, CATEGORIES, []).startswith("# Daily Digest —")


def test_digest_name_is_used_when_given():
    empty = {"dv_uvm": [], "general": []}
    html_out = render_html("2026-01-01", empty, CATEGORIES, [], digest_name="Cooking News Digest")
    md_out = render_markdown("2026-01-01", empty, CATEGORIES, [], digest_name="Cooking News Digest")
    assert "Cooking News Digest" in html_out
    assert md_out.startswith("# Cooking News Digest —")
