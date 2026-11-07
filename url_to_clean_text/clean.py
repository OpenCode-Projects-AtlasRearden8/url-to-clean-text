"""Turn fetched HTML into clean, paste-ready plain text.

Design goals:
- strip site chrome: navigation, ads, cookie banners, scripts, forms
- keep the reading content: headings, paragraphs, lists, tables
- keep link targets without cluttering prose: links become numbered
  footnote references, and the URL list is appended at the end
- optional rich rendering of tables via ``inline_tables``
- no network access and no third-party parsing beyond BeautifulSoup
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


@dataclass
class PageText:
    """Result of cleaning one page."""

    title: str
    text: str
    links: list[tuple[int, str]] = field(default_factory=list)


class EmptyPageError(ValueError):
    """Raised when a page yields no readable text at all."""


# Class/id/attr fragments that scream "site chrome, not content".
_NOISE_FRAGMENTS = re.compile(
    r"(nav|navbar|breadcrumb|sidebar|menu-item|megamenu|hamburger"
    r"|cookie|consent|gdpr|onetrust|cookiebot"
    r"|advert|adsense|sponsor|promo"
    r"|banner|newsletter|subscribe|paywall|metered"
    r"|modal|popup|overlay|lightbox|interstitial"
    r"|skip-link|skip-to|social-share|share-buttons|sharing"
    r"|related-articles|recommended|trending|most-read"
    r"|comment-box|disqus|discourse-comments|signup|cta-banner)",
    re.IGNORECASE,
)

_ROLES_NOISE = {
    "banner",
    "navigation",
    "complementary",
    "contentinfo",
    "dialog",
    "alertdialog",
    "menu",
    "menubar",
    "search",
    "toolbar",
}

_STRIP_TAGS = [
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "math",
    "iframe",
    "object",
    "embed",
    "link",
    "meta",
    "head",
    "form",
    "button",
    "input",
    "select",
    "option",
    "textarea",
    "picture",
    "source",
    "video",
    "audio",
    "canvas",
    "dialog",
    "nav",
    "aside",
    "footer",
    "wbr",
]

_INLINE_TAGS = {
    "a",
    "abbr",
    "b",
    "bdi",
    "bdo",
    "br",
    "cite",
    "code",
    "del",
    "dfn",
    "em",
    "i",
    "ins",
    "kbd",
    "mark",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
}

_HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

_SKIP_HREF = re.compile(r"^(javascript:|data:|#|mailto:|tel:)", re.IGNORECASE)

# "ad-" / "ads_" style tokens must sit at a word boundary so class names like
# "road-details" or "read-more" are not mistaken for ads.
_AD_TOKENS = re.compile(r"(^|[^a-z0-9])ads?(-|_|$)", re.IGNORECASE)

_MAIN_SELECTORS = (
    '[role="main"]',
    '[itemprop="articleBody"]',
    "#content",
    ".post-content",
    ".article-body",
    ".entry-content",
    ".post-body",
    ".markdown-body",
)


def _classes_of(tag: Tag) -> str:
    value = tag.get("class")
    if isinstance(value, str):
        return value
    return " ".join(value or [])


def _is_hidden(tag: Tag) -> bool:
    if tag.has_attr("hidden"):
        return True
    if str(tag.get("aria-hidden", "")).lower() == "true":
        return True
    if str(tag.get("role", "")).strip().lower() in _ROLES_NOISE:
        return True
    style = str(tag.get("style", "")).lower().replace(" ", "")
    if "display:none" in style or "visibility:hidden" in style:
        return True
    return False


def _is_noise(tag: Tag) -> bool:
    if tag.name == "header" and tag.find("nav") is not None:
        return True
    probe = " ".join(
        filter(
            None,
            (
                str(tag.get("id", "")),
                _classes_of(tag),
                str(tag.get("aria-label", "")),
                str(tag.get("data-testid", "")),
            ),
        )
    )
    if _NOISE_FRAGMENTS.search(probe):
        return True
    return any(
        _AD_TOKENS.search(component)
        for component in (str(tag.get("id", "")), _classes_of(tag))
    )


def strip_noise(soup: BeautifulSoup) -> None:
    """Remove scripts, comments, chrome and anything ad/cookie-banner shaped."""
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    # Walk deepest-first so we do not strip a noise container before judging
    # whether an inner content node should survive.
    for tag in sorted(soup.find_all(True), key=lambda t: len(list(t.parents)), reverse=True):
        if tag.decomposed or tag.parent is None:
            continue
        if _is_hidden(tag) or _is_noise(tag):
            tag.decompose()


def _candidates(soup: BeautifulSoup) -> list[Tag]:
    found = list(soup.find_all(["article", "main"]))
    for selector in _MAIN_SELECTORS:
        found.extend(soup.select(selector))
    seen: set[int] = set()
    unique: list[Tag] = []
    for tag in found:
        if id(tag) not in seen:
            seen.add(id(tag))
            unique.append(tag)
    return unique


def pick_main(soup: BeautifulSoup) -> Tag:
    """Choose the element most likely to hold the article body."""
    best: Tag | None = None
    best_score = -1
    for cand in _candidates(soup):
        if cand.decomposed:
            continue
        score = len(cand.get_text(" ", strip=True))
        if score > best_score:
            best, best_score = cand, score
    if best is not None:
        return best
    if soup.body is not None:
        return soup.body
    return soup


class _Renderer:
    def __init__(self, keep_links: bool = True, inline_tables: bool = False) -> None:
        self.keep_links = keep_links
        self.inline_tables = inline_tables
        self.links: list[tuple[int, str]] = []
        self._link_index: dict[str, int] = {}

    # ---- inline content ----------------------------------------------------
    def inline(self, tag: Tag) -> str:
        parts: list[str] = []
        self._inline_into(tag, parts)
        text = "".join(parts)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        return "\n".join(line.strip() for line in text.split("\n")).strip()

    def _inline_into(self, node, parts: list[str]) -> None:
        if isinstance(node, NavigableString):
            parts.append(str(node))
            return
        if not isinstance(node, Tag):
            return
        name = node.name.lower()
        if name in ("script", "style", "svg", "img", "picture", "iframe", "button"):
            return
        if name == "br":
            parts.append("\n")
            return
        if name == "a" and self.keep_links:
            text = node.get_text(" ", strip=True)
            href = (node.get("href") or "").strip()
            if href and not _SKIP_HREF.match(href):
                if href not in self._link_index:
                    number = len(self.links) + 1
                    self._link_index[href] = number
                    self.links.append((number, href))
                label = text.strip() or href
                parts.append(f"{label} [{self._link_index[href]}]")
            elif text:
                parts.append(text)
            return
        for child in node.children:
            self._inline_into(child, parts)

    # ---- blocks ------------------------------------------------------------
    def blocks(self, container: Tag) -> list[str]:
        blocks: list[str] = []
        buffer: list[str] = []

        def flush() -> None:
            text = "".join(buffer).strip()
            buffer.clear()
            if not text:
                return
            text = re.sub(r"[ \t]+", " ", text)
            text = "\n".join(line.strip() for line in text.splitlines()).strip()
            if text:
                blocks.append(text)

        for child in container.children:
            if isinstance(child, NavigableString):
                if str(child).strip() or buffer:
                    buffer.append(str(child))
                continue
            if not isinstance(child, Tag):
                continue
            name = child.name.lower()
            if name in _INLINE_TAGS:
                buffer.append(self.inline(child))
                if name == "br":
                    buffer.append("\n")
                continue
            flush()
            if name == "hr":
                blocks.append("-" * 24)
                continue
            if name in ("script", "style", "img", "picture", "svg", "button", "label"):
                continue
            if name in _HEADING_LEVELS:
                text = self.inline(child)
                if text:
                    blocks.append(f"{'#' * _HEADING_LEVELS[name]} {text}")
            elif name in ("ul", "ol"):
                rendered = self._list(child, indent=0)
                if rendered:
                    blocks.append(rendered)
            elif name == "table":
                rendered = self._table(child)
                if rendered:
                    blocks.append(rendered)
            elif name == "pre":
                code = child.get_text().strip("\n")
                if code.strip():
                    blocks.append("```\n" + code + "\n```")
            elif name == "blockquote":
                inner = self.blocks(child) or [self.inline(child)]
                text = "\n\n".join(b for b in inner if b.strip())
                if text:
                    blocks.append("\n".join("> " + line for line in text.split("\n")))
            elif name == "figure":
                caption = child.find("figcaption")
                if caption is not None:
                    text = self.inline(caption)
                    if text:
                        blocks.append(f"[image caption: {text}]")
            elif name == "dl":
                entries: list[str] = []
                current_key: str | None = None
                for item in child.find_all(["dt", "dd"], recursive=False):
                    if item.name.lower() == "dt":
                        current_key = self.inline(item)
                    elif item.name.lower() == "dd" and current_key:
                        entries.append(f"{current_key}: {self.inline(item)}")
                if entries:
                    blocks.append("\n".join(entries))
            else:
                for block in self.blocks(child):
                    blocks.append(block)
        flush()
        return [b for b in blocks if b.strip()]

    def _list(self, node: Tag, indent: int) -> str:
        ordered = node.name.lower() == "ol"
        lines: list[str] = []
        counter = 0
        for child in node.children:
            if not isinstance(child, Tag) or child.name.lower() != "li":
                continue
            counter += 1
            marker = f"{counter}. " if ordered else "- "
            # Detach nested lists so their content is not repeated inside
            # the parent item's inline text, then render them indented.
            nested = []
            for grandchild in list(child.children):
                if isinstance(grandchild, Tag) and grandchild.name.lower() in ("ul", "ol"):
                    nested.append(grandchild.extract())
            line = self.inline(child)
            if line:
                lines.append(" " * indent + marker + line)
                for sub in nested:
                    sub_text = self._list(sub, indent + 2)
                    if sub_text:
                        lines.append(sub_text)
        return "\n".join(line for line in lines if line.strip())

    def _table(self, table: Tag) -> str:
        rows: list[list[str]] = []
        has_header = False
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False) or tr.find_all(["th", "td"])
            if not cells:
                continue
            if any(c.name.lower() == "th" for c in cells):
                has_header = True
            rows.append([self.inline(c) for c in cells])
        rows = [r for r in rows if any(cell.strip() for cell in r)]
        if not rows:
            return ""
        if not self.inline_tables:
            return "\n".join(" | ".join(row) for row in rows)
        widths = [
            max(len(row[col]) if col < len(row) else 0 for row in rows)
            for col in range(max(len(r) for r in rows))
        ]
        out: list[str] = []
        for i, row in enumerate(rows):
            padded = [
                (row[j] if j < len(row) else "").ljust(widths[j]) for j in range(len(widths))
            ]
            out.append(" | ".join(padded).rstrip())
            if i == 0 and has_header:
                out.append("-+-".join("-" * w for w in widths))
        return "\n".join(out)


def render(
    node: Tag, keep_links: bool = True, inline_tables: bool = False
) -> tuple[str, list[tuple[int, str]]]:
    """Render one page element tree to plain text.

    Returns ``(body_text, links)`` where ``links`` is a list of
    ``(footnote_number, url)`` pairs in order of first appearance.
    """
    renderer = _Renderer(keep_links=keep_links, inline_tables=inline_tables)
    blocks = renderer.blocks(node)
    body = "\n\n".join(blocks)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body, renderer.links


def extract(
    html: str,
    *,
    keep_links: bool = True,
    inline_tables: bool = False,
    include_title: bool = True,
) -> PageText:
    """Clean raw HTML down to plain text.

    Args:
        html: the page markup (pre-fetched).
        keep_links: convert links to numbered footnote references.
        inline_tables: render tables with aligned columns and a separator row.
        include_title: prepend the document title as a heading when present.

    Returns:
        PageText with title, cleaned body text and the footnote link list.

    Raises:
        EmptyPageError: if nothing readable remains after cleaning.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title is not None and soup.title.string is not None:
        title = soup.title.string.strip()
    strip_noise(soup)
    node = pick_main(soup)
    body, links = render(node, keep_links=keep_links, inline_tables=inline_tables)
    if include_title and title and title.lower() not in body[:400].lower():
        body = f"# {title}\n\n{body}" if body else f"# {title}"
    parts = [body]
    if links:
        footnotes = ["Link references:"]
        footnotes.extend(f"[{n}] {url}" for n, url in links)
        parts.append("\n".join(footnotes))
    text = "\n\n".join(p for p in parts if p).strip()
    if not text.strip():
        raise EmptyPageError("no readable text found on this page")
    return PageText(title=title, text=text, links=links)
