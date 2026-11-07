# url-to-clean-text

Fetch a web page and emit **clean plain text**, ready to paste straight into
any AI tool — ChatGPT, Claude, a local model, a notebook, anywhere. Built and
maintained by **Asdale Dynamics, LLC** as part of the free, no-fuss AI tool
collection that goes with *The Massive AI Manual* by Dylan Asdale
(<https://dylanasdale.github.io>).

It is the missing bridge between "this article is buried under cookie
banners" and "here is exactly the content I want the model to read."

## What it does

- **Strips the junk automatically**: navigation bars, sidebars, site footers,
  ad slots, sponsored blocks, newsletter/subscribe boxes, cookie/consent
  banners, hidden elements, scripts, styles and HTML comments.
- **Keeps the reading content**: headings (rendered as Markdown-style `#`
  hashes so structure survives the paste), paragraphs, lists, quotes, code
  blocks and tables.
- **Links become numbered footnotes**, so prose stays readable: the anchor
  text stays inline with a `[1]` marker and a `Link references:` list with
  the URLs sits at the bottom.
- **`--inline-tables`** renders tables as aligned columns with a separator
  row (default is simple `column | column` rows).
- **`--summarize`** sends the cleaned text to a **local, key-free** LLM
  server for an instant digest. Works with Ollama out of the box, plus LM
  Studio, llama.cpp server, LocalAI — anything that speaks the
  OpenAI-compatible `/v1` protocol. No API keys, no cloud, nothing leaves
  your machine unless *you* point it at a remote endpoint.

It is a sibling of two other Asdale Dynamics tools with deliberately
non-overlapping jobs:

| Tool | Reads | Output |
| --- | --- | --- |
| `url-to-clean-text` (this tool) | live web pages / saved HTML | clean text of the page |
| `folder-to-prompt-cli` | local files & folders | a paste-ready project prompt |
| `screenshot-to-text-cli` | images | text extracted from pixels |

## Install

Python 3.9+ is required.

```bash
pip install .
```

That installs the `url-to-clean-text` command (and the `python -m
url_to_clean_text` equivalent).

## Quick start

```bash
# clean text to stdout
url-to-clean-text https://example.com/blog/post

# save to a file, tables aligned
url-to-clean-text https://example.com/blog/post --inline-tables -o post.txt

# from a page you already saved with your browser
url-to-clean-text file://./saved-page.html

# instant digest with a local model (Ollama default, no keys, no cloud)
ollama serve              # once, in another terminal
url-to-clean-text https://example.com/blog/post --summarize

# both the digest and the full text
url-to-clean-text https://example.com/blog/post --summarize-and-keep \
    --model llama3.2
```

## Options

| Flag | Meaning |
| --- | --- |
| `-o, --output FILE` | write the result to a file instead of stdout |
| `--inline-tables` | align table columns and add a separator row |
| `--no-footnotes` | drop link URLs entirely instead of a footnote list |
| `--no-title` | do not prepend the page `<title>` as a heading |
| `--max-chars N` | truncate the final text to N characters |
| `--timeout SECONDS` | network timeout (default 30) |
| `--browser-ua` | use a browser-like user agent (some sites filter scripts) |
| `--summarize` | print only the local-LLM digest |
| `--summarize-and-keep` | print the digest *and* the full clean text |
| `--api-base URL` | OpenAI-compatible endpoint (default: Ollama's `http://localhost:11434/v1`) |
| `--model NAME` | model name on that server (default: `llama3.2`) |
| `--prompt TEXT` | custom digest prompt containing `{content}` |
| `--summary-chars N` | max characters of cleaned text sent to the model |
| `--version` | print version |

Exit codes: `0` success, `2` fetch failed, `3` page had no readable text,
`4` summary request failed.

## Summarizing locally, in plain English

`--summarize` posts a chat request to `{--api-base}/chat/completions`. With
Ollama installed this is zero-config:

```bash
ollama pull llama3.2
url-to-clean-text https://en.wikipedia.org/wiki/Large_language_model --summarize
```

No API key is needed. If `OPENAI_API_KEY` happens to be set in your
environment it is sent as a bearer token so cloud-compatible setups also
work — but the tool never requires it, never asks for it, and never writes
it anywhere.

## For AI tools and agent pipelines

Because the output is deterministic, single-file plain text, it slots neatly
into scripts:

```bash
url-to-clean-text --summarize "$URL" | xclip -selection clipboard   # Linux
url-to-clean-text --summarize "$URL" | pbcopy                       # macOS
```

## Developing

```bash
python -m pytest          # run the test suite
python -m build           # build a wheel
```

Tests cover noise stripping, footnote rendering, table/list rendering and
the CLI end-to-end (including a fake local LLM server — no network needed).

## Privacy

Local-first by design. Fetching a URL talks to that URL and nothing else.
Summaries go only to the endpoint you specify, which is your own machine by
default. No telemetry, no accounts, no secrets in files.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Asdale Dynamics, LLC.

Learn AI "like a friend would" at <https://dylanasdale.github.io>.
