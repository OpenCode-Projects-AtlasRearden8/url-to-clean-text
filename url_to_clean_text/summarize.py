"""Summarize cleaned page text with a local, key-free LLM server.

Works with any OpenAI-compatible ``/v1`` endpoint, so Ollama, LM Studio,
llama.cpp server or LocalAI all work with zero API keys:

    ollama serve                      # or whatever you already run
    url-to-clean-text <url> --summarize \
        --api-base http://localhost:11434/v1 --model llama3.2
"""

from __future__ import annotations

import os

import requests

DEFAULT_API_BASE = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.2"
DEFAULT_MAX_CHARS = 20000
DEFAULT_SUMMARY_CHARS = DEFAULT_MAX_CHARS
DEFAULT_TIMEOUT = 300.0

DEFAULT_PROMPT = (
    "Summarize the following web page in plain, friendly English. "
    "Use 3-6 short bullet points. Do not add opinions or facts that are "
    "not in the text.\n\nTEXT:\n{content}"
)


class SummarizeError(Exception):
    """Raised when the local LLM server fails or returns garbage."""


def summarize(
    text: str,
    *,
    api_base: str = DEFAULT_API_BASE,
    model: str = DEFAULT_MODEL,
    prompt: str = DEFAULT_PROMPT,
    max_chars: int = DEFAULT_MAX_CHARS,
    timeout: float = DEFAULT_TIMEOUT,
    api_key: str | None = None,
) -> str:
    """Send *text* to an OpenAI-compatible endpoint and return its reply.

    No API key is required for local servers; if one is present in the
    ``OPENAI_API_KEY`` environment variable (or passed explicitly) it is
    sent as a bearer token for cloud-compatible setups. Keys are used in
    memory only and are never written to disk by this tool.
    """
    base = api_base.rstrip("/")
    endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
    content = text[:max_chars]
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt.format(content=content)}],
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise SummarizeError(
            f"could not reach summarizer at {endpoint}: {exc}\n"
            "Is your local server running? Tip: `ollama serve` exposes "
            "http://localhost:11434/v1"
        ) from exc
    if response.status_code >= 400:
        raise SummarizeError(
            f"summarizer error (HTTP {response.status_code}) from {endpoint}: "
            f"{response.text[:300]}"
        )
    try:
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise SummarizeError(
            f"unexpected response shape from {endpoint}: {response.text[:300]}"
        ) from exc
    if not isinstance(reply, str) or not reply.strip():
        raise SummarizeError(f"empty summary returned by {endpoint}")
    return reply.strip()
