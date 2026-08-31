## Summary

<!-- What changed, and why. -->

## Testing done

<!--
For a config/feeds.toml change: paste the output of running against
live sources without touching committed state, e.g.

  uv run python -m sundry \
    --html-output /tmp/preview.html --no-write-cache --no-archive

For a code change: which of `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy src`, `uv run pytest` did you run, and did they pass?
-->

## Checklist

- [ ] `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy src` / `uv run pytest` all pass locally
- [ ] If a dependency changed: `uv lock` was run and the updated `uv.lock` is included
- [ ] If `config/feeds.toml` changed: verified it still parses and the new source/category actually produces something (see above)
- [ ] No emoji, no AI-authorship attribution added to code, docs, or commit messages
