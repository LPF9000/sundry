# Security Policy

## Reporting a vulnerability

Please use GitHub's private reporting rather than a public issue: go to
this repository's **Security** tab → **Report a vulnerability**. That
opens a private advisory only visible to maintainers until it's resolved.

If that's not available to you for some reason, open a regular issue
without any exploit details or credentials and ask to be contacted
privately.

## Scope

This project is a GitHub Actions automation that fetches from public
RSS/Atom feeds, the arXiv API, and the Hacker News (Algolia) API — none
of which require credentials — and sends the result over SMTP using a
mail account's app password stored as a repository secret. Relevant
report categories:

- A way to make the workflow leak `MAIL_USERNAME`/`MAIL_PASSWORD` or any
  other secret (e.g. into logs, into the rendered email/archive, into a
  fetched-source's content being echoed back unsanitized).
- A way for a fetched source's content to execute code, rather than just
  being rendered as inert text in the digest (e.g. HTML/script injection
  into the email or Markdown archive that survives the escaping in
  `semiconductor_digest/render.py`).
- Supply-chain concerns in `uv.lock` / `pyproject.toml` (a pinned
  dependency with a known CVE, an unpinned/floating Action version).

Out of scope: the third-party sources themselves (semiengineering.com,
arXiv, Hacker News, etc.) — report issues with those services to their
own maintainers, not here.

## Supported versions

This is a single continuously-deployed tool (no version branches to
maintain) — fixes land on `main` and take effect on the next scheduled
or manually triggered run.
