"""Tests for footnote rendering of links and heading preservation."""

from url_to_clean_text.clean import extract


def test_links_become_numbered_footnotes():
    html = (
        "<html><body><article>"
        "<p>See <a href='https://a.example/one'>first source</a> and "
        "<a href='https://b.example/two'>second source</a>.</p>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "first source [1]" in page.text
    assert "second source [2]" in page.text
    assert "Link references:" in page.text
    assert "[1] https://a.example/one" in page.text
    assert "[2] https://b.example/two" in page.text
    assert page.links == [(1, "https://a.example/one"), (2, "https://b.example/two")]


def test_repeated_link_reuses_footnote_number():
    html = (
        "<html><body><article>"
        "<p><a href='https://x.example/doc'>Doc</a> mentioned again: "
        "<a href='https://x.example/doc'>Doc</a>.</p>"
        "</article></body></html>"
    )
    page = extract(html)
    assert page.links == [(1, "https://x.example/doc")]
    assert page.text.count("Doc [1]") == 2


def test_the_same_link_shared_between_pages_starts_at_1():
    html = "<html><body><p><a href='https://y.example'>link</a></p></body></html>"
    page = extract(html)
    assert page.links[0][0] == 1


def test_no_footnotes_keeps_link_text_only():
    html = (
        "<html><body><article>"
        "<p>Read <a href='https://a.example/one'>the guide</a>.</p>"
        "</article></body></html>"
    )
    page = extract(html, keep_links=False)
    assert "Read the guide." in page.text
    assert "Link references:" not in page.text
    assert page.links == []
    assert "https://" not in page.text


def test_javascript_anchor_links_are_skipped():
    html = (
        "<html><body><article>"
        "<p><a href='javascript:void(0)'>click me</a>"
        "<a href='#section'>jump</a>"
        "<a href='https://real.example/page'>real link</a></p>"
        "</article></body></html>"
    )
    page = extract(html)
    assert page.links == [(1, "https://real.example/page")]
    assert "click me" in page.text  # text kept, no footnote
    assert "real link [1]" in page.text
    assert "[1] https://real.example/page" in page.text


def test_anchor_with_no_text_uses_url():
    html = "<html><body><p><a href='https://z.example'></a><span>x</span></p></body></html>"
    page = extract(html)
    assert page.links == [(1, "https://z.example")]
    assert "https://z.example [1]" in page.text


def test_headings_keep_their_level_as_markdown_hashes():
    html = (
        "<html><body><article>"
        "<h1>Big Topic</h1><h2>Section</h2><h3>Subsection</h3>"
        "<p>text</p>"
        "</article></body></html>"
    )
    page = extract(html, include_title=False)
    assert "# Big Topic" in page.text
    assert "## Section" in page.text
    assert "### Subsection" in page.text


def test_title_prepended_as_heading():
    html = (
        "<html><head><title>Page Title</title></head>"
        "<body><p>body only</p></body></html>"
    )
    page = extract(html)
    assert page.text.startswith("# Page Title")


def test_no_title_mode():
    html = (
        "<html><head><title>Page Title</title></head>"
        "<body><p>body only</p></body></html>"
    )
    page = extract(html, include_title=False)
    assert page.text == "body only"
