"""Command-line entry point: fetch -> dedupe -> classify -> render -> persist."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .cache import SeenCache
from .classify import classify
from .config import DEFAULT_CONFIG_PATH, ConfigError, load_config
from .fetchers import fetch_all
from .models import Article, DigestConfig
from .render import render_html, render_markdown, update_archive_index

# Relative to the current working directory, not this file's location — see
# the comment on config.DEFAULT_CONFIG_PATH for why. All of these assume
# invocation from the repository root, same as every caller in this repo.
DEFAULT_HTML_OUTPUT = Path("digest_output/latest.html")
DEFAULT_ARCHIVE_DIR = Path("digests")
DEFAULT_CACHE_PATH = Path("state/seen.json")

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

EPILOG = """\
examples:
  # Build today's digest using config/feeds.toml, exactly as the daily workflow does
  tech-news-digest

  # Preview a build without touching committed state (safe to run anytime)
  tech-news-digest --html-output /tmp/preview.html --no-write-cache --no-archive

  # Point at a config living somewhere else (e.g. a different topic)
  tech-news-digest --config path/to/feeds.toml

See config/feeds.toml to add sources/categories, or AGENTS.md if you're
an AI agent setting this up for a new topic. Full docs: README.md.
"""

logger = logging.getLogger("tech_news_digest")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tech-news-digest",
        description=__doc__,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to feeds.toml")
    parser.add_argument("--html-output", type=Path, default=DEFAULT_HTML_OUTPUT, help="Where to write the email HTML")
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR, help="Markdown archive directory")
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH, help="Seen-URL dedupe cache path")
    parser.add_argument(
        "--no-write-cache",
        action="store_true",
        help="Don't persist the seen-URL cache. Use for PR previews / dry runs so a test build "
        "can't suppress tomorrow's real digest.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Don't write/update the Markdown archive. Use for PR previews / dry runs.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        type=str.upper,
        choices=LOG_LEVELS,
        help="Python logging level (default: INFO)",
    )
    return parser.parse_args(argv)


def build_digest(config: DigestConfig, cache: SeenCache) -> tuple[dict[str, list[Article]], list[str]]:
    """Fetch, dedupe against `cache`, classify, and cap every category.

    Newly-shown article URLs are recorded into `cache` in memory; call
    `cache.save()` yourself afterward if the result should be persisted.
    """
    raw_articles, failures = fetch_all(config)
    logger.info("Fetched %d raw items before dedupe/classification.", len(raw_articles))

    # Dedupe by URL across sources, then drop anything already sent before.
    by_url = {article.link: article for article in raw_articles}
    new_articles = [article for article in by_url.values() if article.link not in cache]

    categorized: dict[str, list[Article]] = {category.key: [] for category in config.categories}
    for article in new_articles:
        categorized[classify(article, config.categories)].append(article)

    max_items_by_key = {key: category.max_items for key, category in config.category_by_key().items()}
    now = datetime.now(UTC)
    for key, items in categorized.items():
        items.sort(key=lambda article: article.published or now, reverse=True)
        categorized[key] = items[: max_items_by_key[key]]

    for items in categorized.values():
        for article in items:
            cache.add(article.link)

    return categorized, failures


def _log_summary(categorized: dict[str, list[Article]], config: DigestConfig, failures: list[str]) -> int:
    """Log a per-category breakdown so a run's outcome is legible without opening the output file."""
    total_shown = sum(len(items) for items in categorized.values())
    unique_urls_shown = {article.link for items in categorized.values() for article in items}
    logger.info("Showing %d new item(s) across %d unique URL(s):", total_shown, len(unique_urls_shown))

    by_key = config.category_by_key()
    for key, items in categorized.items():
        if items:
            logger.info("  %-45s %d", by_key[key].title, len(items))

    if failures:
        logger.warning("Source failures today: %s", failures)

    return total_shown


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(name)s: %(message)s")

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error(
            "Config file not found: %s\n"
            "  Expected a feeds.toml there. Run this from the repository root, or pass "
            "--config explicitly.\n"
            "  Setting up a new topic? See AGENTS.md or README.md's 'Using this for your "
            "own topic'.",
            args.config,
        )
        return 1
    except ConfigError as exc:
        logger.error("Invalid config at %s:\n  %s", args.config, exc)
        return 1

    cache = SeenCache(args.cache_path)

    categorized, failures = build_digest(config, cache)
    total_shown = _log_summary(categorized, config, failures)

    run_date = datetime.now(UTC).strftime("%Y-%m-%d")

    args.html_output.parent.mkdir(parents=True, exist_ok=True)
    args.html_output.write_text(
        render_html(run_date, categorized, config.categories, failures, config.digest_name), encoding="utf-8"
    )
    logger.info("Wrote %s", args.html_output)

    if not args.no_archive:
        args.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = args.archive_dir / f"{run_date}.md"
        archive_path.write_text(
            render_markdown(run_date, categorized, config.categories, failures, config.digest_name),
            encoding="utf-8",
        )
        update_archive_index(args.archive_dir, run_date)
        logger.info("Wrote %s", archive_path)

    if not args.no_write_cache:
        cache.save()

    _write_github_actions_outputs(config.digest_name, run_date, total_shown)
    return 0


def _write_github_actions_outputs(digest_name: str, run_date: str, total_shown: int) -> None:
    """Expose the email subject/send-gate to later workflow steps, if running in CI."""
    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        return
    item_word = "item" if total_shown == 1 else "items"
    subject = f"{digest_name} — {run_date} ({total_shown} new {item_word})"
    with open(github_env, "a", encoding="utf-8") as f:
        f.write(f"DIGEST_SUBJECT={subject}\n")
        f.write("DIGEST_HAS_CONTENT=true\n")


if __name__ == "__main__":
    sys.exit(main())
