# STATUS — url-to-clean-text

**Project:** url-to-clean-text
**Owner:** Asdale Dynamics, LLC
**Date:** 2026-11-07
**Status:** Working CLI, tested, published locally as a wheel (not on PyPI)

## What was built

A Python CLI that fetches a URL and emits clean plain text, ready to paste
into any AI tool.

- `url_to_clean_text/clean.py` — the extraction engine:
  - strips scripts, styles, HTML comments, navigation bars, sidebars,
    site footers, ad slots, sponsored/promo blocks, newsletter & subscribe
    boxes, cookie/consent banners (incl. OneTrust-style), hidden elements,
    `aria-hidden`, noise roles (`banner`, `navigation`, ...), forms
  - picks the article body heuristically (`<article>` / `<main>` /
    common content classes, scored by text length; falls back to `<body>`)
  - keeps headings as Markdown-style `#` hashes so structure survives paste
  - keeps paragraphs, lists (incl. nested), blockquotes (as `>` lines),
    code blocks (fenced), definition lists, image captions
  - links survive as numbered footnotes: inline `text [1]` markers plus a
    `Link references:` URL list at the end (deduped by URL; JS/#/mailto
    hrefs dropped)
  - tables default to `cell | cell` rows; with `inline_tables=True` they
    render as aligned columns with a `-+-` separator row under headers
- `url_to_clean_text/fetch.py` — fetches http/https (`requests`) and
  `file://` paths for saved pages and offline testing; friendly errors
- `url_to_clean_text/summarize.py` — optional instant digest via any local
  OpenAI-compatible `/v1` endpoint; **Ollama works with zero configuration
  and zero API keys** (`http://localhost:11434/v1` is the default); an
  `OPENAI_API_KEY` env var is used only if you already have one, never
  stored or logged
- `url_to_clean_text/cli.py` — argparse CLI, exit codes (0 ok / 2 fetch /
  3 empty / 4 summarize), `python -m url_to_clean_text` entry point too
- `tests/` — 41 tests: noise stripping, footnote rendering, table/list
  rendering, CLI end-to-end via `file://` URLs and a fake local LLM server

Sibling tools with non-overlapping jobs: `folder-to-prompt-cli` (local
files) and `screenshot-to-text-cli` (images).

## How to run it

```bash
pip install .            # from this folder; provides `url-to-clean-text`

url-to-clean-text https://example.com/blog/post
url-to-clean-text https://example.com --inline-tables -o post.txt
url-to-clean-text file://./saved-page.html --no-footnotes
url-to-clean-text https://example.com --summarize            # Ollama default
url-to-clean-text https://example.com --summarize-and-keep --model llama3.2
```

## Verification results (all run locally, today)

- `python -m pytest -q` → **41 passed**
- `python -m build` → wheel built successfully
- Wheel installed into a clean venv; `url-to-clean-text --version` →
  `url-to-clean-text 0.1.0`; `file://` page extraction verified
- Live network check: `url-to-clean-text https://example.com` produced
  clean title + body text, exit code 0
- Boundary-safety check for ad-class heuristics: `ad-slot`/`advert*` removed
  while `road-details`/`read-more` content survived
- `LICENSE` contains exactly: `Copyright (c) 2026 Asdale Dynamics, LLC`
- README credits Asdale Dynamics, LLC
- No secrets, API keys, or personal data in any file (summaries default to
  `localhost`; keys are only read from the environment, never written)

## Known gaps

- Article-body detection is heuristic. Very unusual layouts (canvas apps,
  heavy JS renderers, reader paywalls) may return little or wrong text;
  `--browser-ua` helps with soft bot walls, but full JS rendering (e.g.
  Playwright) is out of scope for v0.1
- Some sites may still slip obfuscated cookie banners past the heuristics;
  the noise-attribute list is easy to extend and PRs welcome
- `--summarize` assumes the endpoint exposes OpenAI-style
  `/chat/completions`; native Ollama `/api/generate` is not used
- No PDF support (that belongs in a future sibling tool or a follow-on)
- Tables with `colspan`/`rowspan` are flattened cell-by-cell, not merged

## Legal

MIT License. Copyright (c) 2026 Asdale Dynamics, LLC.
