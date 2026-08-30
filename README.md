# semiconductor-news

A daily, self-updating digest of public research and news relevant to
**Design Verification, UVM, RTL/architecture, mixed-signal, DFT & advanced
packaging, hardware security/cryptography, RISC-V & processor architecture,
EDA tools/flows, and the conferences where it all gets presented** — DVCon,
DAC, ISSCC, Hot Chips, CHES, and friends.

It runs entirely on a scheduled **GitHub Actions** workflow, pulls only
from free/public sources (no scraping behind logins, no paid APIs), and
emails you a digest every day. It also keeps a browsable Markdown archive
of every day's digest in [`digests/`](./digests).

## How it works

```
scripts/feeds.yaml   → sources, categories, and keyword rules (edit this to tune)
scripts/digest.py    → fetches, dedupes, classifies, and renders the digest
state/seen.json      → cache of URLs already sent, so nothing repeats
digests/YYYY-MM-DD.md→ the archived copy of each day's digest
digest_output/       → scratch dir for the HTML the email step sends (gitignored)
```

Each run:
1. Pulls the latest items from a set of RSS/Atom feeds, the public
   **arXiv API** (`cs.AR` Hardware Architecture + hardware-flavored
   `cs.CR` Crypto & Security), and the **Hacker News (Algolia) API** for a
   handful of topic searches.
2. Drops anything already sent in the last ~45 days (`state/seen.json`).
3. Buckets what's left into topic categories by keyword match (see
   `scripts/feeds.yaml`).
4. Renders an HTML email + a Markdown archive page, commits the archive
   back to the repo, and emails the HTML version to you.

If a source is down or a feed breaks, that source is skipped for the day
(logged, and noted at the bottom of the email) rather than failing the
whole run — nothing to babysit.

## One-time setup (~5 minutes)

Email requires an SMTP account to send *from* — GitHub Actions can't send
mail on its own. The easiest free option is your own Gmail account with an
**App Password** (works even if the sending account and recipient are the
same address):

1. On the Google Account used to send: turn on 2-Step Verification, then
   create an **App Password** at
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (choose "Mail" / "Other").
2. In this repo: **Settings → Secrets and variables → Actions → New
   repository secret**, add:
   - `MAIL_USERNAME` — the Gmail address sending the digest
   - `MAIL_PASSWORD` — the 16-character App Password from step 1
3. **Settings → Actions → General → Workflow permissions** → set to
   **"Read and write permissions"** (needed so the workflow can commit the
   daily archive file back to the repo).
4. Done. The workflow runs daily at **12:00 UTC**; you can also trigger it
   on demand from the **Actions** tab → "Daily Semiconductor & DV Digest"
   → **Run workflow**, which is the fastest way to confirm everything's
   wired up correctly.

Recipient is hardcoded to `bestasitis@gmail.com` in
`.github/workflows/daily-digest.yml` — change the `to:` line there if that
ever needs to change.

Using a provider other than Gmail? Swap `server_address`/`server_port` in
the workflow for your provider's SMTP details (see the
[action-send-mail docs](https://github.com/dawidd6/action-send-mail)).

## Tuning it

Everything content-related lives in `scripts/feeds.yaml`, no code changes
needed:
- Add/remove an RSS feed under `rss_sources` (set `default_category` if a
  feed is 100% on-topic already, e.g. a pure crypto research feed).
- Add/remove an arXiv search under `arxiv_sources`.
- Add/remove a Hacker News search term under `hn_queries`.
- Add, remove, or reweight a category (title, blurb, `max_items`,
  `keywords`) under `categories`.

Change the send time by editing the `cron` line in
`.github/workflows/daily-digest.yml` (always UTC).

## Current topic coverage

- 🧪 **Design Verification, UVM & Formal** — testbenches, coverage,
  assertions (SVA), formal methods, CDC, portable stimulus, emulation.
- 🛠️ **RTL, HDLs, Architecture & EDA Flows** — RTL/architecture research,
  SystemVerilog language updates, newer HDLs (Chisel, Amaranth, SpinalHDL,
  MyHDL), high-level synthesis, novel/domain-specific architectures, and
  new or interesting EDA tools and flows (including open-source EDA:
  OpenROAD, OpenLane, Yosys).
- 📈 **Mixed-Signal & Analog** — AMS design/verification, data converters,
  PLLs, SerDes.
- 🔬 **DFT, Test & Advanced Packaging** — ATPG, scan/JTAG, chiplets, UCIe,
  2.5D/3D integration, HBM.
- 🔐 **Cryptography & Hardware Security** — side-channel attacks, PUFs,
  root-of-trust, post-quantum crypto, hardware trojans, secure boot.
- ⚙️ **RISC-V & Processor Architecture** — new cores, microarchitecture,
  ISA news, general CPU/SoC architecture.
- 🎤 **Conferences & Industry Events** — DVCon, DAC, ISSCC, Hot Chips,
  CHES, ICCAD, DATE, CICC, calls for papers.
- 📰 **General Semiconductor & Industry News** — catch-all for context
  (fabs, supply chain, market moves).

### Related topics worth adding later

A few adjacent areas that came up while scoping this but aren't dedicated
categories yet — say the word and they're a `feeds.yaml` edit away:
- **Power-aware design & low-power verification** (UPF, clock/power gating)
- **Functional safety** (ISO 26262) for automotive silicon
- **AI/ML accelerator architecture** (NPUs/TPUs, systolic arrays)
- **Quantum computing hardware** (adjacent to the post-quantum crypto beat)
- **Semiconductor policy & supply chain** (CHIPS Act, export controls) if
  you want that beyond what already surfaces incidentally in general news
- Vendor-specific EDA blogs (Synopsys/Cadence/Siemens) — skipped for now
  since they don't offer reliable public RSS; worth revisiting if they add
  one, or via a periodic web-search step instead of RSS.

## Notes

- First run's `state/seen.json` is empty, so day one will show the most
  recent items across every category (capped at each category's
  `max_items`) rather than a "new since yesterday" set — normal, and it
  settles into a true daily-delta digest from day two onward.
- Nothing here requires paid APIs or ongoing maintenance; sources going
  offline just quietly drop out of that day's digest (and are named in the
  email footer) instead of breaking anything.
