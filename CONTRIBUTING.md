# Contributing

Thanks for considering a contribution. This project has two kinds of
"contribution," and it's worth being clear about which one you're making:

- **You want your own topic digest** (different field, different sources).
  You don't need to contribute anything here — fork the repo and edit
  `config/feeds.toml`. See the "Using this for your own topic" section in
  the [README](./README.md). That's the intended way to reuse this project,
  and no permission or PR is needed.
- **You want to improve *this* digest** (a better source, a sharper
  keyword, a real bug, a genuinely reusable feature). That's what the rest
  of this file covers.

## Before you start

- **New source or keyword tweak?** Just open a PR — these are low-risk,
  reviewed quickly.
- **New feature, new fetcher type, or a behavior change?** Open an issue
  first describing what and why. Saves both of us from a PR built on a
  misunderstanding of scope.
- **Found a bug?** Open an issue with what you expected vs. what happened,
  and, if you can, the smallest input that reproduces it.

## Development setup

Dependency management is [uv](https://docs.astral.sh/uv/).
[Install it](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync --extra dev
```

## Before opening a PR

Run the same checks CI runs, and make sure they're clean:

```bash
uv run ruff check .              # lint
uv run ruff format .             # format
uv run mypy src                  # type-check
uv run pytest                    # unit tests
```

If you touched `config/feeds.toml`, sanity-check it actually builds a
digest from live sources without writing anything back to committed state:

```bash
uv run python -m semiconductor_digest \
  --html-output /tmp/preview.html \
  --no-write-cache --no-archive
```

If you added or changed a dependency in `pyproject.toml`, run `uv lock`
and commit the updated `uv.lock` alongside it.

## What makes a good PR here

- **Small and scoped.** One source, one keyword fix, one bug — not a
  drive-by rewrite of something unrelated.
- **Tests included** for anything in `src/semiconductor_digest/` — the
  existing suite runs against mocked HTTP (see `tests/test_fetchers.py`
  for the pattern), never live network calls.
- **No emoji, no AI-authorship attribution** in code, docs, or commit
  messages — see the note at the top of the README if that's unclear.
- **A new source belongs in `config/feeds.toml`, not in code.** If you
  find yourself editing `src/` just to add a feed, something's off —
  open an issue instead; the source list is meant to be pure data.

## Reporting a security issue

See [SECURITY.md](./SECURITY.md) — please don't open a public issue for
anything that looks like a credential leak or similar.
