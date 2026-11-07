"""Tests for list and table rendering (default pipe rows + --inline-tables)."""

from url_to_clean_text.clean import extract


def test_tables_default_pipe_rows():
    html = (
        "<html><body><article>"
        "<table><tr><th>Item</th><th>Price</th></tr>"
        "<tr><td>Apple</td><td>$1</td></tr>"
        "<tr><td>Pear</td><td>$2</td></tr></table>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "Item | Price" in page.text
    assert "Apple | $1" in page.text
    assert "Pear | $2" in page.text


def test_tables_inline_mode_adds_aligned_separator():
    html = (
        "<html><body><article>"
        "<table><tr><th>Item</th><th>Price</th></tr>"
        "<tr><td>Apple</td><td>$1</td></tr>"
        "<tr><td>Pear</td><td>$2</td></tr></table>"
        "</article></body></html>"
    )
    page = extract(html, inline_tables=True)
    lines = page.text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if "Item" in line and "Price" in line)
    separator = lines[header_index + 1]
    assert separator and set(separator) == {"-", "+"}
    # columns are aligned: padded header and cell rows share column width
    header_cols = lines[header_index].split(" | ")
    row_cols = lines[header_index + 2].split(" | ")
    assert len(header_cols) == len(row_cols) == 2
    assert len(header_cols[0]) == len(row_cols[0]) == 5  # widest is "Apple"


def test_tables_inline_mode_without_header_has_no_separator():
    html = (
        "<html><body><article>"
        "<table><tr><td>1</td><td>2</td></tr>"
        "<tr><td>3</td><td>4</td></tr></table>"
        "</article></body></html>"
    )
    page = extract(html, inline_tables=True)
    lines = page.text.splitlines()
    assert "1" in lines[0] and "2" in lines[0]
    assert not any(set(line) == {"-", "+"} for line in lines)


def test_empty_and_noise_tables_are_dropped():
    html = (
        "<html><body><article>"
        "<table><tr><td></td><td>   </td></tr></table>"
        "<table><tr><td>kept</td></tr></table>"
        "</article></body></html>"
    )
    page = extract(html)
    assert page.text == "kept"


def test_bullets_and_ordered_lists_render():
    html = (
        "<html><body><article>"
        "<ul><li>one</li><li>two</li></ul>"
        "<ol><li>first</li><li>second</li></ol>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "- one" in page.text
    assert "- two" in page.text
    assert "1. first" in page.text
    assert "2. second" in page.text


def test_nested_lists_indent_without_repetition():
    html = (
        "<html><body><article>"
        "<ul><li>outer<ul><li>inner</li></ul></li></ul>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "outer" in page.text
    assert "inner" in page.text
    # "outer" line must not already contain "inner"
    outer_line = next(l for l in page.text.splitlines() if l.strip().startswith("- outer") or "outer" in l)
    assert "inner" not in outer_line


def test_pre_blocks_keep_newlines():
    html = (
        "<html><body><article>"
        "<pre>line one\n    line two</pre>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "```\nline one\n    line two\n```" in page.text


def test_blockquote_rendered_with_prefix():
    html = (
        "<html><body><article>"
        "<blockquote><p>quoted wisdom</p></blockquote>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "> quoted wisdom" in page.text


def test_image_captions_kept_images_dropped():
    html = (
        "<html><body><article>"
        "<figure><img src='pic.png'><figcaption>Fig 1. A chart</figcaption></figure>"
        "</article></body></html>"
    )
    page = extract(html)
    assert "[image caption: Fig 1. A chart]" in page.text
