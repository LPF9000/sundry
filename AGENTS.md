# AGENTS.md

Instructions for AI coding agents (Claude Code, Cursor, Codex, Copilot,
etc.) working in or with this repository. Humans: see [README.md](./README.md)
instead — this file is written for a machine to act on.

## What this repo is

A daily digest pipeline: fetch public RSS/Atom feeds + the arXiv API + the
Hacker News (Algolia) API → dedupe → classify into topic categories by
keyword → render an HTML email + Markdown archive entry → email it, via a
scheduled GitHub Actions workflow. The Python package
(`src/tech_news_digest/`) is generic — it knows nothing about any
particular topic, and this repo ships no default topic of its own.
All topic-specific content (sources, categories, keywords) lives in one
file — `feeds.toml` — that lives in the *user's* repo, not here. See
`examples/feeds.toml` for an annotated example, and
[semiconductor-news-digest](https://github.com/LPF9000/semiconductor-news-digest)
for a complete real-world instance built on this engine.

## The most common task: set this up for a new topic

If a user asks you to "make a daily digest about X using this," **do not
fork this repository.** Point them at the reusable GitHub Actions
workflow this repo publishes instead — it lets their own repo pull in the
digest engine without copying any Python code. Concretely:

1. In the **user's own repo** (new or existing — it needs no relation to
   this one), run:

   ```bash
   uvx --from "git+https://github.com/LPF9000/tech-news-digest.git@v2.0.0" tech-news-digest init
   ```

   This writes `config/feeds.toml` and `.github/workflows/digest.yml`
   there, already wired up correctly — nothing to hand-write, no paths to
   get wrong. It prints the exact next steps below when it runs.
2. Fill in the TODOs it left in `config/feeds.toml` for the user's topic
   — use the schema reference below, or just do it yourself from their
   description of the topic and any sources/keywords they mention.
3. Tell the user to set three things in their repo's GitHub settings —
   this is the only manual step, you cannot do it for them:
   - Secrets `MAIL_USERNAME` / `MAIL_PASSWORD` (a Gmail address + an
     [App Password](https://myaccount.google.com/apppasswords))
   - Variable `DIGEST_RECIPIENT` (who receives the email)
   - **Settings > Actions > General > Workflow permissions** → "Read and
     write permissions" (so it can commit the daily archive)
4. That's the entire setup. No `pip install`, no cloning this repo, no
   copying `src/`. The reusable workflow installs the digest engine
   straight from this repo's tagged release at run time.

If the user instead wants to **modify the engine itself** (a new fetcher
type, different classification logic), *then* forking is correct — see
[CONTRIBUTING.md](./CONTRIBUTING.md).

## `config/feeds.toml` schema

```toml
# Optional. Title used in the email/archive header and email subject.
# Defaults to "Daily Digest" if omitted.
digest_name = "Your Topic Digest"

# Optional. Hacker News (Algolia) search terms — plain strings.
# MUST appear before any [[...]] table below (TOML attaches bare
# key = value lines to the most recently opened table, not the document
# root — putting hn_queries after a [[rss_sources]] block silently makes
# it a field of the last rss_sources entry instead of top-level).
hn_queries = ["search term one", "search term two"]

# Zero or more RSS/Atom feeds.
[[rss_sources]]
name = "Human-readable source name"
url = "https://example.com/feed.xml"
# Optional: force every item from this feed into one category regardless
# of keyword score. Use for a feed that's already 100% on-topic.
default_category = "some_category_key"

# Zero or more arXiv API searches (https://info.arxiv.org/help/api/index.html).
[[arxiv_sources]]
name = "Human-readable search name"
query = 'cat:cs.AR AND abs:"some phrase"'
max_results = 25  # optional, default 20

# One or more categories, in the order you want them to appear.
# Exactly one category MUST have key = "general" — it's the catch-all
# for anything that scores zero keyword matches; config loading raises
# if it's missing.
[[categories]]
key = "unique_snake_case_key"
title = "Human-readable Category Title"
blurb = "One or two sentences shown under the title, explaining what this category covers and why it matters."
max_items = 8  # cap on how many items this category shows per run
keywords = [
  "keyword one",
  "keyword two",
  # matched case-insensitively as a substring of title+summary;
  # a title match scores double a summary-only match. Pad short/ambiguous
  # terms with spaces, e.g. " ai " not "ai", to avoid matching inside
  # unrelated words.
]
```

Validate a new config actually builds something before telling the user
it's done:

```bash
uv sync --extra dev
uv run python -m tech_news_digest \
  --config config/feeds.toml \
  --html-output /tmp/preview.html \
  --no-write-cache --no-archive
```

A `FileNotFoundError`/`ConfigError` from that command prints a clear
reason (missing categories, no `general` key, an unknown
`default_category`, etc.) — read it, it's written to be actionable.

## Conventions to respect in this repo

- **No emoji** anywhere — code, docs, commit messages, or rendered
  digest output (category titles included).
- **No AI-authorship attribution anywhere in this repo** — not in code,
  comments, rendered output, commit messages, or PR bodies. No
  "Generated by ..." footers, no naming which tool or model made a
  change. If whatever you're using appends one automatically, strip it
  before committing/posting.
- **Commit messages and PR descriptions read like a person wrote them**:
  plain, concise, describing *what changed and why* (the intent). Don't
  narrate your own process, don't reference or quote the request that
  prompted the change.
- **Source/category data belongs in a `feeds.toml`, never in `src/`.**
  If a task seems to require editing `src/tech_news_digest/` just to add
  a source or keyword, something is wrong — stop and reconsider; see
  "set this up for a new topic" above. This repo's own `examples/`
  holds a schema demo, not a real topic — a real topic's config lives in
  the user's own repo, not here.
- **Keep secrets out of committed files and logs.** Nothing in this repo
  should ever need a secret to run a dry build (`--no-write-cache
  --no-archive` needs no credentials at all).

## Dev commands (this repo's own Python package)

```bash
uv sync --extra dev              # install
uv run ruff check .              # lint
uv run ruff format .             # format
uv run mypy src                  # type-check
uv run pytest                    # unit tests (mocked HTTP, no network)
```

All four must pass before a commit to `src/` or `tests/` is finished.
See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution bar.
