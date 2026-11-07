"""Command-line interface for url-to-clean-text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .clean import EmptyPageError, extract
from .fetch import BROWSER_USER_AGENT, DEFAULT_USER_AGENT, FetchError, fetch
from .summarize import (
    DEFAULT_API_BASE,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_SUMMARY_CHARS,
    SummarizeError,
    summarize,
)

EXIT_OK = 0
EXIT_FETCH = 2
EXIT_EMPTY = 3
EXIT_SUMMARY = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="url-to-clean-text",
        description=(
            "Fetch a URL and print clean plain text ready to paste into any "
            "AI chat, notebook or editor. Strips navigation, ads, cookie "
            "banners and script noise; keeps headings; renders links as "
            "numbered footnotes at the end."
        ),
        epilog=(
            "Examples:\n"
            "  url-to-clean-text https://example.com/article\n"
            "  url-to-clean-text https://example.com --no-footnotes\n"
            "  url-to-clean-text https://example.com --inline-tables -o page.txt\n"
            "  url-to-clean-text https://example.com --summarize --model llama3.2\n"
            "  url-to-clean-text file://./saved-page.html\n"
            "\nHonest-robots respect: nothing is tracked, nothing leaves your "
            "machine unless you use --summarize with a remote endpoint."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="URL to fetch (http, https or file://)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write result to FILE instead of stdout",
    )
    parser.add_argument(
        "--inline-tables",
        action="store_true",
        help="render tables with aligned columns and a separator row",
    )
    parser.add_argument(
        "--no-footnotes",
        action="store_true",
        help="discard link URLs instead of adding a footnote list at the end",
    )
    parser.add_argument(
        "--no-title",
        action="store_true",
        help="do not prepend the page <title> as a heading",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        metavar="N",
        help="truncate the final text to at most N characters",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="network timeout for fetching (default: 30)",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help=f"user agent header to send (default: {DEFAULT_USER_AGENT})",
    )
    parser.add_argument(
        "--browser-ua",
        action="store_true",
        help=f"use a plain browser user agent instead ({BROWSER_USER_AGENT[:40]}...)",
    )
    digest = parser.add_argument_group("instant digest (local LLM, no keys)")
    digest.add_argument(
        "--summarize",
        action="store_true",
        help=(
            "send the extracted text to a local OpenAI-compatible endpoint "
            "and print a short digest instead of the full text"
        ),
    )
    digest.add_argument(
        "--summarize-and-keep",
        action="store_true",
        help="print both the summary and the full cleaned text",
    )
    digest.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"OpenAI-compatible base URL (default: {DEFAULT_API_BASE}; Ollama's is exactly this)",
    )
    digest.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"model name on the server (default: {DEFAULT_MODEL})",
    )
    digest.add_argument(
        "--prompt",
        default=None,
        help='custom summary prompt using {content} (default built-in)',
    )
    digest.add_argument(
        "--summary-chars",
        type=int,
        default=DEFAULT_SUMMARY_CHARS,
        metavar="N",
        help=f"maximum characters of cleaned text to send (default: {DEFAULT_SUMMARY_CHARS})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    user_agent = BROWSER_USER_AGENT if args.browser_ua else args.user_agent

    try:
        html = fetch(args.url, timeout=args.timeout, user_agent=user_agent)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FETCH

    try:
        page = extract(
            html,
            keep_links=not args.no_footnotes,
            inline_tables=args.inline_tables,
            include_title=not args.no_title,
        )
    except EmptyPageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_EMPTY

    if args.max_chars is not None and args.max_chars >= 0:
        page_text = page.text[: args.max_chars]
    else:
        page_text = page.text

    if args.summarize or args.summarize_and_keep:
        try:
            summary = summarize(
                page.text,
                api_base=args.api_base,
                model=args.model,
                prompt=args.prompt or DEFAULT_PROMPT,
                max_chars=args.summary_chars,
            )
        except SummarizeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_SUMMARY
        if args.summarize_and_keep:
            return _emit(f"Summary:\n{summary}\n\n---\n\n{page_text}", args)
        return _emit(summary, args)

    return _emit(page_text, args)


def _emit(text: str, args) -> int:
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {Path(args.output).stat().st_size} bytes to {args.output}", file=sys.stderr)
    else:
        print(text)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
