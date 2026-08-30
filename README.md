# semiconductor-news

[![CI](https://github.com/LPF9000/semiconductor-news/actions/workflows/ci.yml/badge.svg)](https://github.com/LPF9000/semiconductor-news/actions/workflows/ci.yml)
[![Daily Digest](https://github.com/LPF9000/semiconductor-news/actions/workflows/daily-digest.yml/badge.svg)](https://github.com/LPF9000/semiconductor-news/actions/workflows/daily-digest.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A daily, self-updating digest of public research and news relevant to
Design Verification, UVM, RTL/architecture, mixed-signal, DFT and advanced
packaging, hardware security/cryptography, RISC-V and processor
architecture, EDA tools/flows, and the conferences where it all gets
presented: DVCon, DAC, ISSCC, Hot Chips, CHES, and others.

It runs entirely on a scheduled GitHub Actions workflow, pulls only from
free/public sources (no scraping behind logins, no paid APIs), and emails
a digest every day. It also keeps a browsable Markdown archive of every
day's digest in [`digests/`](./digests).

## Using this for your own topic

Nothing here is semiconductor-specific in *how* it works — only in
`config/feeds.toml`'s content. **You don't need to fork this repository
to reuse it.**

### Recommended: no fork, no copied code

This repo publishes itself as a reusable GitHub Actions workflow
(`.github/workflows/digest-reusable.yml`). Any repo — new or existing,
yours, unrelated to this one — can pull in the whole digest engine with
one config file and a 12-line workflow:

1. In **your own repo**, create `config/feeds.toml` — see
   [Tuning the digest](#tuning-the-digest) for the schema, or hand the
   schema to an AI agent (see [For AI agents](#for-ai-agents) below) and
   describe your topic.
2. Add `.github/workflows/digest.yml`:

   ```yaml
   name: Daily Digest
   on:
     schedule:
       - cron: "0 12 * * *"
     workflow_dispatch: {}
   permissions:
     contents: write
   jobs:
     digest:
       uses: LPF9000/semiconductor-news/.github/workflows/digest-reusable.yml@v1.0.0
       with:
         recipient: ${{ vars.DIGEST_RECIPIENT }}
       secrets:
         MAIL_USERNAME: ${{ secrets.MAIL_USERNAME }}
         MAIL_PASSWORD: ${{ secrets.MAIL_PASSWORD }}
   ```

3. In your repo's settings, set secrets `MAIL_USERNAME`/`MAIL_PASSWORD`
   and variable `DIGEST_RECIPIENT` (same steps as
   [Setting up email](#setting-up-email-required-one-time) below, just in
   *your* repo), and flip **Workflow permissions** to "Read and write."

That's the entire setup. Nothing to clone, no Python to install locally,
no copy of `src/semiconductor_digest/` to keep in sync with this repo's
own updates — `@v1.0.0` always installs this project's tagged release
straight from GitHub at run time. This mirrors how a real GitHub Action
is meant to be consumed (see
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
> from https://github.com/LPF9000/semiconductor-news (see its
> `AGENTS.md`) in this repo. Sources: [any specific sites/feeds you
> already know]. I want it emailed to **[your address]**.

is enough for a capable agent to write `config/feeds.toml`, add the
caller workflow, and tell you exactly which three settings to fill in in
your repo (it can't set secrets for you — that's a manual step by
design).

## Contents

- [Using this for your own topic](#using-this-for-your-own-topic)
- [For AI agents](#for-ai-agents)
- [Setting up email (required, one-time)](#setting-up-email-required-one-time)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Continuous integration](#continuous-integration)
- [Tuning the digest](#tuning-the-digest)
- [Local development](#local-development)
- [Topic coverage](#topic-coverage)
- [Related topics worth adding later](#related-topics-worth-adding-later)
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
   select **"Read and write permissions"** — the daily workflow needs
   this to commit each day's archive file back to the repository.
4. That's it. The daily workflow runs at **12:00 UTC**; you can also
   trigger it on demand from the **Actions** tab -> "Daily Semiconductor
   & DV Digest" -> **Run workflow**, which is the fastest way to confirm
   everything is wired up correctly.

Every pull request also builds a real digest from live sources and, once
the secrets above are set, emails you a preview of it before merge — see
[Continuous integration](#continuous-integration).

The recipient defaults to `bestasitis@gmail.com` (this fork's original
owner) but is overridable without touching any YAML: set a
**`DIGEST_RECIPIENT`** repository variable at **Settings > Secrets and
variables > Actions > Variables tab > New repository variable**, and
both workflows pick it up automatically. If you forked this for your
own topic, set this — otherwise your digest emails the previous owner.

Using a provider other than Gmail? Swap `server_address`/`server_port` in
both workflow files for your provider's SMTP details (see the
[action-send-mail docs](https://github.com/dawidd6/action-send-mail)).

## How it works

Each run:

1. Fetches the latest items from a set of RSS/Atom feeds, the public
   arXiv API (`cs.AR` Hardware Architecture, plus a hardware-flavored
   `cs.CR` Crypto & Security search), and the Hacker News (Algolia) API
   for a handful of topic searches — concurrently, so one slow source
   doesn't hold up the rest.
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
config/feeds.toml          Source, category, and keyword configuration
src/semiconductor_digest/  The digest package (fetch, classify, render, CLI)
tests/                     Unit tests (mocked HTTP — no live network calls)
digests/YYYY-MM-DD.md      Archived copy of each day's digest
state/seen.json            Cross-run dedupe cache
digest_output/             Scratch dir for the HTML the email step sends (gitignored)
uv.lock                    Locked, reproducible dependency versions (uv)
AGENTS.md                  Setup instructions for AI coding agents (see "For AI agents")
CLAUDE.md                  Pointer to AGENTS.md, for Claude Code specifically
.github/workflows/ci.yml              PR checks + live preview email
.github/workflows/daily-digest.yml    This repo's own scheduled run (local install)
.github/workflows/digest-reusable.yml The reusable workflow external repos call (git install)
.github/actions/           Composite action shared by ci.yml and daily-digest.yml
```

`semiconductor_digest` is a proper installable Python package (not a
loose script): typed with dataclasses and `from __future__ import
annotations` throughout, one module per concern (`fetchers/`, `classify`,
`cache`, `render`, `config`, `cli`), and covered by a unit test suite that
runs against mocked HTTP responses rather than live sources.

## Continuous integration

Every pull request runs `.github/workflows/ci.yml`:

1. **Lint GitHub Actions workflows** — [actionlint](https://github.com/rhysd/actionlint)
   over every workflow file, catching real workflow bugs (bad expressions,
   unknown contexts, shellcheck issues in `run:` blocks), not just YAML
   syntax.
2. **Lint & test** — `ruff check`, `ruff format --check`, `mypy`, and the
   `pytest` suite, on Python 3.11 and 3.12.
3. **Build & email a preview digest** — runs the real pipeline against
   live sources (no commit, no cache write, so it can't suppress or
   pollute tomorrow's real digest) and, if the mail secrets are
   configured, emails you the result prefixed `[PR Preview]` so you can
   see exactly what a merge would produce before merging it. If the
   secrets aren't set yet, this step is skipped with a warning instead of
   failing the PR.

The daily workflow (`.github/workflows/daily-digest.yml`) reuses the same
composite action (`.github/actions/setup-python-env`) to install the
package via [uv](https://docs.astral.sh/uv/) from the committed
`uv.lock`, so both workflows always set up their environment identically
and reproducibly — no "works on my machine" dependency drift.
`.github/workflows/digest-reusable.yml` is the third workflow in this
repo — it's what external callers `uses:` (see
["Using this for your own topic"](#using-this-for-your-own-topic)), not
something this repo's own daily run calls into itself; the two are kept
separate deliberately, see the comment at the top of that file for why.

Dependencies are kept current automatically by
[Dependabot](.github/dependabot.yml) (weekly, for both Python
dependencies — GitHub's `pip` ecosystem also covers `uv.lock` projects —
and GitHub Actions versions). A [pre-commit](.pre-commit-config.yaml)
config mirrors the CI lint checks for anyone who wants them to run
locally on every commit — `uv run pre-commit install` (or
`pip install pre-commit && pre-commit install` if you'd rather not add
it as a project dependency).

## Tuning the digest

Everything content-related lives in `config/feeds.toml` — no code changes
needed:

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

Change the send time by editing the `cron` line in
`.github/workflows/daily-digest.yml` (always UTC).

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

uv run python -m semiconductor_digest --help   # see all CLI flags
uv run python -m semiconductor_digest \
  --html-output /tmp/preview.html \
  --no-write-cache --no-archive                # build a preview without touching repo state
```

Added or changed a dependency in `pyproject.toml`? Run `uv lock` and
commit the updated `uv.lock` alongside it.

## Topic coverage

- **Design Verification, UVM & Formal** — testbenches, coverage,
  assertions (SVA), formal methods, CDC, portable stimulus, emulation.
- **RTL, HDLs, Architecture & EDA Flows** — RTL/architecture research,
  SystemVerilog language updates, newer HDLs (Chisel, Amaranth,
  SpinalHDL, MyHDL), high-level synthesis, novel/domain-specific
  architectures, and new or interesting EDA tools and flows (including
  open-source EDA: OpenROAD, OpenLane, Yosys).
- **Mixed-Signal & Analog** — AMS design/verification, data converters,
  PLLs, SerDes.
- **DFT, Test & Advanced Packaging** — ATPG, scan/JTAG, chiplets, UCIe,
  2.5D/3D integration, HBM.
- **Cryptography & Hardware Security** — side-channel attacks, PUFs,
  root-of-trust, post-quantum crypto, hardware trojans, secure boot.
- **RISC-V & Processor Architecture** — new cores, microarchitecture, ISA
  news, general CPU/SoC architecture.
- **Conferences & Industry Events** — DVCon, DAC, ISSCC, Hot Chips, CHES,
  ICCAD, DATE, CICC, calls for papers.
- **General Semiconductor & Industry News** — catch-all for context
  (fabs, supply chain, market moves).

### Related topics worth adding later

A few adjacent areas that came up while scoping this but aren't dedicated
categories yet — say the word and they're a `config/feeds.toml` edit
away:

- Power-aware design & low-power verification (UPF, clock/power gating)
- Functional safety (ISO 26262) for automotive silicon
- AI/ML accelerator architecture (NPUs/TPUs, systolic arrays)
- Quantum computing hardware (adjacent to the post-quantum crypto beat)
- Semiconductor policy & supply chain (CHIPS Act, export controls), if
  you want that beyond what already surfaces incidentally in general news
- Vendor-specific EDA blogs (Synopsys/Cadence/Siemens) — skipped for now
  since they don't offer reliable public RSS; worth revisiting if they
  add one, or via a periodic web-search step instead of RSS.

## Operational notes

- The first run's `state/seen.json` is empty, so day one shows the most
  recent items across every category (capped at each category's
  `max_items`) rather than a "new since yesterday" set. This is expected,
  and it settles into a true daily-delta digest from day two onward.
- Nothing here requires paid APIs or ongoing maintenance. Sources going
  offline just quietly drop out of that day's digest (and are named in
  the email footer) instead of breaking anything.
- Config is TOML, parsed with Python's standard-library `tomllib`
  (3.11+) — reading `config/feeds.toml` needs zero third-party
  dependencies.

## Contributing

Improving *this* tool (a source, a bug, a real feature) vs. wanting your
own topic digest are different things — see
[CONTRIBUTING.md](./CONTRIBUTING.md) for which applies and how to set up
a dev environment, run the checks, and open a PR. This project follows
the [Contributor Covenant](./CODE_OF_CONDUCT.md). Found a security issue?
See [SECURITY.md](./SECURITY.md) rather than a public issue.

## License

[MIT](./LICENSE) — use, fork, and modify freely.
