"""Fetch a URL's HTML.

Kept deliberately thin: ``requests`` for http(s) URLs, plain file reads for
``file://`` URLs (handy for offline/local-first use and for the test suite).
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import requests

DEFAULT_USER_AGENT = (
    "url-to-clean-text/{version} (+local-first text extractor; no tracking)"
)

# Naive bot walls vary; a plain browser-ish UA maximizes the chance of
# getting real HTML back from sites that filter obvious scripts.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


class FetchError(Exception):
    """Raised when a URL cannot be fetched."""


def fetch(
    url: str,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    """Return the (decoded) HTML body for *url*.

    Supports ``http://``, ``https://`` and ``file://`` schemes.

    Raises:
        FetchError: on network failure, non-200 status or unreadable file.
    """
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme == "file":
        return _fetch_file(url)
    if scheme not in ("http", "https", ""):
        raise FetchError(f"unsupported URL scheme: {scheme!r} (use http, https or file)")
    if not scheme:
        url = "https://" + url
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise FetchError(f"could not fetch {url}: {exc}") from exc
    if response.status_code >= 400:
        raise FetchError(f"could not fetch {url}: HTTP {response.status_code}")
    if not response.text or not response.text.strip():
        raise FetchError(f"could not fetch {url}: empty response body")
    return response.text


def _fetch_file(url: str) -> str:
    path = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path))
    if not path.is_file():
        raise FetchError(f"file not found: {path}")
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FetchError(f"could not read {path}: {exc}") from exc


__all__ = ["DEFAULT_USER_AGENT", "BROWSER_USER_AGENT", "FetchError", "fetch"]
