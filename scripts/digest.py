#!/usr/bin/env python3
"""
Daily semiconductor / design-verification news digest.

Pulls from a set of public RSS/Atom feeds, the arXiv API, and the Hacker
News (Algolia) API — no API keys required — buckets items into topic
categories by keyword matching, drops anything already sent before (via a
committed seen-URL cache), and renders:

  - digest_output/latest.html   (for the email step)
  - digests/YYYY-MM-DD.md       (archived to the repo, human-browsable)
  - state/seen.json             (updated dedupe cache)

All source/category/keyword configuration lives in scripts/feeds.yaml —
edit that file to tune what shows up, not this script.
"""

from __future__ import annotations

import calendar
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FEEDS_CONFIG = REPO_ROOT / "scripts" / "feeds.yaml"
DIGEST_OUTPUT_DIR = REPO_ROOT / "digest_output"
DIGESTS_ARCHIVE_DIR = REPO_ROOT / "digests"
STATE_DIR = REPO_ROOT / "state"
SEEN_CACHE_PATH = STATE_DIR / "seen.json"

# How long a URL stays in the dedupe cache before it's allowed to be
# pruned out (keeps the cache file from growing forever).
SEEN_CACHE_TTL_DAYS = 45

USER_AGENT = (
    "Mozilla/5.0 (compatible; semiconductor-news-digest/1.0; "
    "+https://github.com/lpf9000/semiconductor-news)"
)
HTTP_TIMEOUT = 20
ARXIV_API = "http://export.arxiv.org/api/query"
HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search_by_date"

MAX_SUMMARY_CHARS = 240


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def load_config() -> dict:
    with open(FEEDS_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------
# Fetchers — each returns a list of raw item dicts and appends to
# `failures` on any error instead of raising, so one dead source never
# takes down the whole run.
# --------------------------------------------------------------------------

def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val:
            try:
                return datetime.fromtimestamp(calendar.timegm(val), tz=timezone.utc)
            except (OverflowError, ValueError):
                continue
    return None


def fetch_rss(name: str, url: str, default_category: str | None, failures: list) -> list[dict]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # noqa: BLE001 - a dead feed must not kill the run
        failures.append(f"{name} ({exc.__class__.__name__})")
        return []

    if parsed.bozo and not parsed.entries:
        failures.append(f"{name} (unparseable feed)")
        return []

    items = []
    for entry in parsed.entries:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue
        summary = strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        items.append(
            {
                "title": strip_html(title),
                "link": link,
                "summary": truncate(summary),
                "published": entry_datetime(entry),
                "source": name,
                "forced_category": default_category,
            }
        )
    return items


def fetch_arxiv(name: str, query: str, max_results: int, failures: list) -> list[dict]:
    url = f"{ARXIV_API}?search_query={quote(query)}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{name} ({exc.__class__.__name__})")
        return []

    items = []
    for entry in parsed.entries:
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue
        authors = ", ".join(a.get("name", "") for a in getattr(entry, "authors", []) if a.get("name"))
        summary = strip_html(getattr(entry, "summary", ""))
        if authors:
            summary = f"{authors} — {summary}"
        items.append(
            {
                "title": strip_html(title).replace("\n", " "),
                "link": link,
                "summary": truncate(summary),
                "published": entry_datetime(entry),
                "source": name,
                "forced_category": None,
            }
        )
    # arXiv's API asks for a small courtesy delay between calls.
    time.sleep(3)
    return items


def fetch_hn(queries: list[str], failures: list) -> list[dict]:
    items = []
    for q in queries:
        try:
            resp = requests.get(
                HN_ALGOLIA_API,
                params={"query": q, "tags": "story", "hitsPerPage": 6},
                headers={"User-Agent": USER_AGENT},
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Hacker News: '{q}' ({exc.__class__.__name__})")
            continue

        for hit in data.get("hits", []):
            title = hit.get("title") or hit.get("story_title")
            link = hit.get("url") or (
                f"https://news.ycombinator.com/item?id={hit.get('objectID')}" if hit.get("objectID") else None
            )
            points = hit.get("points") or 0
            if not title or not link or points < 3:
                continue
            published = None
            created_at = hit.get("created_at")
            if created_at:
                try:
                    published = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    pass
            items.append(
                {
                    "title": strip_html(title),
                    "link": link,
                    "summary": f"{points} points on Hacker News (discussion: "
                    f"https://news.ycombinator.com/item?id={hit.get('objectID')})",
                    "published": published,
                    "source": "Hacker News",
                    "forced_category": None,
                }
            )
    return items


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def classify(item: dict, categories: list[dict]) -> str:
    if item.get("forced_category"):
        return item["forced_category"]

    haystack = f" {item['title'].lower()} {item['summary'].lower()} "
    best_key, best_score = "general", 0
    for cat in categories:
        if cat["key"] == "general":
            continue
        score = 0
        title_lower = item["title"].lower()
        for kw in cat.get("keywords") or []:
            kw = kw.lower()
            if kw in title_lower:
                score += 2
            elif kw in haystack:
                score += 1
        if score > best_score:
            best_key, best_score = cat["key"], score
    return best_key


# --------------------------------------------------------------------------
# Seen-URL cache (dedupe across daily runs)
# --------------------------------------------------------------------------

def load_seen_cache() -> dict:
    if not SEEN_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(SEEN_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen_cache(cache: dict) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_CACHE_TTL_DAYS)
    pruned = {}
    for url, first_seen in cache.items():
        try:
            ts = datetime.fromisoformat(first_seen)
        except ValueError:
            continue
        if ts >= cutoff:
            pruned[url] = first_seen
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_CACHE_PATH.write_text(json.dumps(pruned, indent=2, sort_keys=True), encoding="utf-8")


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def fmt_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%b %d")


def render_html(run_date: str, categorized: dict, cat_meta: dict, failures: list) -> str:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'></head>",
        "<body style=\"margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,"
        "Segoe UI,Helvetica,Arial,sans-serif;color:#18181b;\">",
        "<div style=\"max-width:680px;margin:0 auto;padding:24px 16px;\">",
        f"<h1 style=\"font-size:20px;margin:0 0 4px;\">Semiconductor &amp; DV Daily Digest</h1>",
        f"<p style=\"margin:0 0 24px;color:#71717a;font-size:13px;\">{run_date}</p>",
    ]

    any_items = any(categorized.get(key) for key in cat_meta)
    if not any_items:
        parts.append(
            "<p style='font-size:14px;'>Quiet day — no new items across any tracked source "
            "since yesterday's run. The pipeline is alive and will keep checking.</p>"
        )

    for key, meta in cat_meta.items():
        items = categorized.get(key, [])
        if not items:
            continue
        parts.append(
            f"<h2 style=\"font-size:16px;margin:28px 0 4px;border-bottom:2px solid #e4e4e7;"
            f"padding-bottom:6px;\">{meta['title']}</h2>"
        )
        parts.append(f"<p style=\"margin:0 0 12px;color:#52525b;font-size:12.5px;\">{meta['blurb'].strip()}</p>")
        for item in items:
            date_str = fmt_date(item["published"])
            meta_line = " · ".join(x for x in (item["source"], date_str) if x)
            parts.append(
                "<div style=\"margin:0 0 14px;\">"
                f"<a href=\"{html.escape(item['link'])}\" style=\"font-size:14.5px;font-weight:600;"
                f"color:#1d4ed8;text-decoration:none;\">{html.escape(item['title'])}</a><br>"
                f"<span style=\"font-size:11.5px;color:#71717a;\">{html.escape(meta_line)}</span><br>"
                f"<span style=\"font-size:13px;color:#3f3f46;\">{html.escape(item['summary'])}</span>"
                "</div>"
            )

    if failures:
        parts.append(
            "<p style=\"margin-top:28px;font-size:11px;color:#a1a1aa;\">"
            f"Sources that couldn't be reached today: {html.escape('; '.join(failures))}</p>"
        )

    parts.append(
        "<p style=\"margin-top:24px;font-size:11px;color:#a1a1aa;\">Generated automatically by the "
        "GitHub Actions workflow in this repo. Tune sources/keywords in scripts/feeds.yaml, "
        "or browse the archive in digests/.</p>"
    )
    parts.append("</div></body></html>")
    return "".join(parts)


def render_markdown(run_date: str, categorized: dict, cat_meta: dict, failures: list) -> str:
    lines = [f"# Semiconductor & DV Daily Digest — {run_date}", ""]

    any_items = any(categorized.get(key) for key in cat_meta)
    if not any_items:
        lines.append("_Quiet day — no new items across any tracked source since the last run._")

    for key, meta in cat_meta.items():
        items = categorized.get(key, [])
        if not items:
            continue
        lines.append(f"## {meta['title']}")
        lines.append(f"_{meta['blurb'].strip()}_")
        lines.append("")
        for item in items:
            date_str = fmt_date(item["published"])
            meta_line = " · ".join(x for x in (item["source"], date_str) if x)
            lines.append(f"- **[{item['title']}]({item['link']})** — {meta_line}")
            if item["summary"]:
                lines.append(f"  {item['summary']}")
        lines.append("")

    if failures:
        lines.append(f"_Sources that couldn't be reached today: {'; '.join(failures)}_")
        lines.append("")

    return "\n".join(lines)


def update_archive_index(run_date: str) -> None:
    index_path = DIGESTS_ARCHIVE_DIR / "README.md"
    default_header = "# Digest archive\n\nOne file per day, newest first.\n"
    content = index_path.read_text(encoding="utf-8") if index_path.exists() else default_header
    entry = f"- [{run_date}](./{run_date}.md)"

    lines = content.splitlines()
    if entry in lines:
        return

    insert_at = next((i for i, line in enumerate(lines) if line.startswith("- [")), len(lines))
    lines.insert(insert_at, entry)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    config = load_config()
    categories = config["categories"]
    cat_meta = {c["key"]: c for c in categories}
    failures: list[str] = []

    raw_items: list[dict] = []

    for src in config.get("rss_sources", []):
        raw_items.extend(fetch_rss(src["name"], src["url"], src.get("default_category"), failures))

    for src in config.get("arxiv_sources", []):
        raw_items.extend(fetch_arxiv(src["name"], src["query"], src.get("max_results", 20), failures))

    raw_items.extend(fetch_hn(config.get("hn_queries", []), failures))

    print(f"Fetched {len(raw_items)} raw items before dedupe/classification.", file=sys.stderr)

    seen = load_seen_cache()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Dedupe by URL (across sources and across days).
    dedup: dict[str, dict] = {}
    for item in raw_items:
        dedup.setdefault(item["link"], item)

    new_items = [item for item in dedup.values() if item["link"] not in seen]

    categorized: dict[str, list[dict]] = {c["key"]: [] for c in categories}
    for item in new_items:
        key = classify(item, categories)
        categorized[key].append(item)

    for key, items in categorized.items():
        items.sort(key=lambda it: it["published"] or datetime.now(timezone.utc), reverse=True)
        categorized[key] = items[: cat_meta[key].get("max_items", 8)]

    # Only URLs actually shown get marked "seen" — anything cut by the
    # per-category cap stays eligible to surface (and get capped again)
    # tomorrow, rather than disappearing silently forever.
    shown_urls = {item["link"] for items in categorized.values() for item in items}
    for url in shown_urls:
        seen[url] = now_iso
    save_seen_cache(seen)

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_shown = sum(len(v) for v in categorized.values())
    print(f"Showing {total_shown} new items today across {len(shown_urls)} unique URLs.", file=sys.stderr)
    if failures:
        print(f"Source failures: {failures}", file=sys.stderr)

    html_out = render_html(run_date, categorized, cat_meta, failures)
    md_out = render_markdown(run_date, categorized, cat_meta, failures)

    DIGEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (DIGEST_OUTPUT_DIR / "latest.html").write_text(html_out, encoding="utf-8")

    DIGESTS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    (DIGESTS_ARCHIVE_DIR / f"{run_date}.md").write_text(md_out, encoding="utf-8")
    update_archive_index(run_date)

    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        subject = f"Semiconductor & DV Digest — {run_date} ({total_shown} new item{'s' if total_shown != 1 else ''})"
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"DIGEST_SUBJECT={subject}\n")
            # Always send — even a "quiet day" note is a useful liveness signal —
            # but the workflow can gate on this if that's ever unwanted.
            f.write("DIGEST_HAS_CONTENT=true\n")


if __name__ == "__main__":
    main()
