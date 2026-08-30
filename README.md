# tech-news-digest

[![CI](https://github.com/LPF9000/tech-news-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/LPF9000/tech-news-digest/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A reusable, config-driven tool that fetches public news/research sources
on a schedule and emails you a daily digest — built and run entirely on
GitHub Actions, no server to host. This repo is the engine only: it ships
no default topic, and nothing about how it works is tied to any one
subject. Repointing it at any subject is a config file, not a code
change — see [Using this for your own topic](#using-this-for-your-own-topic),
or [semiconductor-news-digest](https://github.com/LPF9000/semiconductor-news-digest)
for a complete real-world example built on this engine.

It pulls only from free/public sources (no scraping behind logins, no
paid APIs). Whatever repo you point it at ends up with its own browsable
Markdown archive of every day's digest, committed alongside its config.

## Using this for your own topic

**You don't need to fork this repository to reuse it.**

### Recommended: no fork, no copied code

This repo publishes itself as a reusable GitHub Actions workflow
(`.github/workflows/digest-reusable.yml`) and a scaffolding command. Any
repo — new or existing, yours, unrelated to this one — can pull in the
whole digest engine with one config file and a short workflow:

1. In **your own repo**, run:

   ```bash
   uvx --from "git+https://github.com/LPF9000/tech-news-digest.git@v2.0.0" tech-news-digest init
   ```

   This writes `config/feeds.toml` and `.github/workflows/digest.yml`
   for you, already pointed at the right repo and ref — nothing to
   copy-paste or get wrong. It prints the exact next steps when it runs.
2. Fill in the TODOs it left in `config/feeds.toml` — see
   [Tuning the digest](#tuning-the-digest) for the schema, or hand the
   file to an AI agent (see [For AI agents](#for-ai-agents) below) along
   with a description of your topic.
3. In your repo's settings, set secrets `MAIL_USERNAME`/`MAIL_PASSWORD`
   and variable `DIGEST_RECIPIENT` (same steps as
   [Setting up email](#setting-up-email-required-one-time) below, just in
   *your* repo), and flip **Workflow permissions** to "Read and write."

That's the entire setup. Nothing to clone, no Python to install locally,
no copy of `src/tech_news_digest/` to keep in sync with this repo's own
updates — `@v2.0.0` always installs this project's tagged release
straight from GitHub at run time, both for `init` and for the daily run
itself. This mirrors how a real GitHub Action is meant to be consumed
(see
[GitHub's own reusable-workflows docs](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)),
not a fork-and-diverge template.

### Alternative: fork it

Only do this if you want to change the *engine itself* (a new fetcher
type, different classification/rendering logic) — see
[CONTRIBUTING.md](./CONTRIBUTING.md). If you just want your own topic,
forking means maintaining a permanent divergent copy of code you'll
never actually need to touch; use the reusable workflow above instead.

## For AI agents

Working with an AI coding assistant (Claude Code, Cursor, Codex, Copilot,
etc.)? This repo ships [AGENTS.md](./AGENTS.md) — machine-readable setup
instructions following the [agents.md](https://agents.md) cross-tool
convention, so your agent can read it directly rather than you having to
paraphrase this README. A prompt like:

> Set up a daily digest for **[your topic]** using the reusable workflow
> from https://github.com/LPF9000/tech-news-digest (see its `AGENTS.md`)
> in this repo. Sources: [any specific sites/feeds you already know]. I
> want it emailed to **[your address]**.

is enough for a capable agent to run `tech-news-digest init`, fill in
`config/feeds.toml` for your topic, and tell you exactly which three
settings to fill in in your repo (it can't set secrets for you — that's
a manual step by design).

## Contents

- [Using this for your own topic](#using-this-for-your-own-topic)
- [For AI agents](#for-ai-agents)
- [Setting up email (required, one-time)](#setting-up-email-required-one-time)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Continuous integration](#continuous-integration)
- [Tuning the digest](#tuning-the-digest)
- [Local development](#local-development)
- [Example: semiconductor-news-digest](#example-semiconductor-news-digest)
- [Operational notes](#operational-notes)
- [Contributing](#contributing)
- [License](#license)

## Setting up email (required, one-time)

GitHub Actions cannot send mail on its own — it needs an SMTP account to
send *from*. The easiest free option is a Gmail account with an **App
Password** (this works even when the sending account and the recipient
are the same address).

1. On the Google Account that will send the digest: turn on 2-Step
   Verification, then create an App Password at
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (choose "Mail" / "Other" as the app).
2. In this repository, go to **Settings > Secrets and variables >
   Actions > New repository secret** and add two secrets:

   | Secret name     | Value                                          |
   | ---------------- | ---------------------------------------------- |
   | `MAIL_USERNAME`  | The Gmail address sending the digest            |
   | `MAIL_PASSWORD`  | The 16-character App Password from step 1       |

3. Go to **Settings > Actions > General > Workflow permissions** and
   select **"Read and write permissions"** — the workflow needs this to
   commit each day's archive file back to the repository.
4. That's it. In a repo using the reusable workflow, the schedule runs at
   whatever cron the caller workflow sets (`0 12 * * *` — 12:00 UTC — by
   default from `tech-news-digest init`); you can also trigger it on
   demand from the **Actions** tab, which is the fastest way to confirm
   everything is wired up correctly.

These same secrets, set here in *this* repo, are also what let this
repo's own CI build and email you a preview digest from
[`examples/feeds.toml`](./examples/feeds.toml) on every pull request —
see [Continuous integration](#continuous-integration). They're unrelated
to, and don't need to match, the secrets you set in a repo that uses the
reusable workflow for a real topic.

The recipient defaults to `bestasitis@gmail.com` (this repo's owner) but
is overridable without touching any YAML: set a **`DIGEST_RECIPIENT`**
repository variable at **Settings > Secrets and variables > Actions >
Variables tab > New repository variable**.

Using a provider other than Gmail? Swap `server_address`/`server_port` in
[`ci.yml`](./.github/workflows/ci.yml) (or, for a repo using the reusable
workflow, its `mail-server`/`mail-port` inputs) for your provider's SMTP
details (see the
[action-send-mail docs](https://github.com/dawidd6/action-send-mail)).

## How it works

Each run:

1. Fetches the latest items from a set of RSS/Atom feeds, the public
   arXiv API, and the Hacker News (Algolia) API for a handful of topic
   searches — concurrently, so one slow source doesn't hold up the rest.
2. Drops anything already sent in the last ~45 days, tracked in
   `state/seen.json`.
3. Buckets what's left into topic categories by keyword match (see
   `config/feeds.toml`), capping each category to its configured size.
4. Renders an HTML email and a Markdown archive page, commits the
   archive back to the repository, and emails the HTML version.

If a source is down or a feed breaks, that source is simply skipped for
the day — logged, and named at the bottom of the email — rather than
failing the whole run. Nothing here needs to be babysat.

## Repository layout

```
src/tech_news_digest/      The digest package (fetch, classify, render, CLI, scaffold)
examples/feeds.toml        Annotated example config — schema demo, not a real topic
tests/                     Unit tests (mocked HTTP — no live network calls)
digest_output/             Scratch dir for the HTML the email step sends (gitignored)
uv.lock                    Locked, reproducible dependency versions (uv)
AGENTS.md                  Setup instructions for AI coding agents (see "For AI agents")
CLAUDE.md                  Pointer to AGENTS.md, for Claude Code specifically
.github/workflows/ci.yml              PR checks + a preview email built from examples/feeds.toml
.github/workflows/digest-reusable.yml The reusable workflow external repos call (git install)
.github/actions/           Composite action used by ci.yml
```

A repo that uses the reusable workflow (like
[semiconductor-news-digest](https://github.com/LPF9000/semiconductor-news-digest))
gets its own `config/feeds.toml`, `.github/workflows/digest.yml`,
`digests/YYYY-MM-DD.md` archive, and `state/seen.json` dedupe cache — none
of that lives in this repo.

`tech_news_digest` is a proper installable Python package (not a loose
script): typed with dataclasses and `from __future__ import annotations`
throughout, one module per concern (`fetchers/`, `classify`, `cache`,
`render`, `config`, `cli`), and covered by a unit test suite that runs
against mocked HTTP responses rather than live sources.

## Continuous integration

Every pull request runs `.github/workflows/ci.yml`:

1. **Lint GitHub Actions workflows** — [actionlint](https://github.com/rhysd/actionlint)
   over every workflow file, catching real workflow bugs (bad expressions,
   unknown contexts, shellcheck issues in `run:` blocks), not just YAML
   syntax.
2. **Lint & test** — `ruff check`, `ruff format --check`, `mypy`, and the
   `pytest` suite, on Python 3.11 and 3.12.
3. **Build & email a preview digest** — runs the real pipeline against
   [`examples/feeds.toml`](./examples/feeds.toml) and live sources (no
   commit, no cache write) and, if the mail secrets are configured,
   emails you the result prefixed `[PR Preview]` so you can confirm the
   engine still works end to end before merging. If the secrets aren't
   set yet, this step is skipped with a warning instead of failing the PR.

`ci.yml` installs the package via [uv](https://docs.astral.sh/uv/) from
the committed `uv.lock` (through the shared
`.github/actions/setup-python-env` composite action), so every run sets
up its environment identically and reproducibly — no "works on my
machine" dependency drift. `.github/workflows/digest-reusable.yml` is the
other workflow in this repo — it's what external callers `uses:` (see
["Using this for your own topic"](#using-this-for-your-own-topic)); this
repo doesn't call it on itself, since it has no topic of its own to
build — see the comment at the top of that file for why.

Dependencies are kept current automatically by
[Dependabot](.github/dependabot.yml) (weekly, for both Python
dependencies — GitHub's `pip` ecosystem also covers `uv.lock` projects —
and GitHub Actions versions). A [pre-commit](.pre-commit-config.yaml)
config mirrors the CI lint checks for anyone who wants them to run
locally on every commit — `uv run pre-commit install` (or
`pip install pre-commit && pre-commit install` if you'd rather not add
it as a project dependency).

## Tuning the digest

Everything content-related lives in your repo's `feeds.toml` — no code
changes needed:

- Set `digest_name` (top-level key) to control the title shown in the
  email header, archive header, and email subject line.
- Add or remove an RSS feed under `[[rss_sources]]` (set
  `default_category` if a feed is already 100% on-topic, e.g. a pure
  crypto research feed).
- Add or remove an arXiv search under `[[arxiv_sources]]`.
- Add or remove a Hacker News search term in the top-level `hn_queries`
  list.
- Add, remove, or reweight a category (`title`, `blurb`, `max_items`,
  `keywords`) under `[[categories]]`.

Change the send time by editing the `cron` line in your repo's
`.github/workflows/digest.yml` (always UTC).

## Local development

Dependency management is [uv](https://docs.astral.sh/uv/) — fast, and
installs are reproducible from the committed `uv.lock` rather than
whatever happens to resolve on the day you run it.
[Install uv](https://docs.astral.sh/uv/getting-started/installation/) once,
then:

```bash
uv sync --extra dev       # creates .venv/ and installs exactly what's in uv.lock

uv run ruff check .              # lint
uv run ruff format .             # format
uv run mypy src                  # type-check
uv run pytest                    # unit tests (mocked HTTP, no network needed)

uv run python -m tech_news_digest --help   # see all CLI flags
uv run python -m tech_news_digest \
  --config examples/feeds.toml \
  --html-output /tmp/preview.html \
  --no-write-cache --no-archive            # build a preview without touching repo state

uv run python -m tech_news_digest init /tmp/some-other-repo  # try the scaffolder
```

Added or changed a dependency in `pyproject.toml`? Run `uv lock` and
commit the updated `uv.lock` alongside it.

## Example: semiconductor-news-digest

[semiconductor-news-digest](https://github.com/LPF9000/semiconductor-news-digest)
is a complete, real-world instance built on this engine — a semiconductor
design/verification topic (UVM, RTL, mixed-signal, DFT, hardware
security, RISC-V, EDA flows, conferences) with nothing in it but
`config/feeds.toml` and the caller workflow, exactly like [Using this for
your own topic](#using-this-for-your-own-topic) describes. It's the
reference to copy from if you want to see a fully tuned config, not just
the annotated stub in `examples/`.

## Operational notes

- The first run's `state/seen.json` is empty, so day one shows the most
  recent items across every category (capped at each category's
  `max_items`) rather than a "new since yesterday" set. This is expected,
  and it settles into a true daily-delta digest from day two onward.
- Nothing here requires paid APIs or ongoing maintenance. Sources going
  offline just quietly drop out of that day's digest (and are named in
  the email footer) instead of breaking anything.
- Config is TOML, parsed with Python's standard-library `tomllib`
  (3.11+) — reading `feeds.toml` needs zero third-party dependencies.

## Contributing

Improving *this* tool (a source, a bug, a real feature) vs. wanting your
own topic digest are different things — see
[CONTRIBUTING.md](./CONTRIBUTING.md) for which applies and how to set up
a dev environment, run the checks, and open a PR. This project follows
the [Contributor Covenant](./CODE_OF_CONDUCT.md). Found a security issue?
See [SECURITY.md](./SECURITY.md) rather than a public issue.

## License

[MIT](./LICENSE) — use, fork, and modify freely.
