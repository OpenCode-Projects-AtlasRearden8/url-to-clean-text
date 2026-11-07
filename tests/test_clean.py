"""Tests for noise stripping: nav, ads, cookie banners, scripts, chrome."""

import pytest

from url_to_clean_text.clean import EmptyPageError, extract


def extract_body(html: str) -> str:
    return extract(html, include_title=True).text


def test_script_and_style_are_removed():
    html = (
        "<html><head><style>.x{color:red}</style></head><body>"
        "<script>alert('noise')</script>"
        "<p>keep me</p>"
        "<style>p{}</style></body></html>"
    )
    text = extract_body(html)
    assert "keep me" in text
    assert "noise" not in text
    assert "color:red" not in text


def test_nav_and_footer_removed():
    html = (
        "<html><body>"
        "<nav><a href='/home'>Home</a> | <a href='/about'>About</a></nav>"
        "<article><p>The actual article.</p></article>"
        "<footer>privacy policy contact us</footer>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "The actual article." in text
    assert "Home" not in text
    assert "About" not in text
    assert "privacy policy" not in text


def test_cookie_banner_removed():
    html = (
        "<html><body>"
        "<div id='cookie-banner' class='cookie-consent'>"
        "We value your privacy. Accept all cookies?"
        "</div>"
        "<p>Real content lives here.</p>"
        "<div class='onetrust-pc-sdk'>Manage preferences</div>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "Real content lives here." in text
    assert "cookies" not in text.lower()
    assert "Manage preferences" not in text


def test_ad_and_sponsor_blocks_removed():
    html = (
        "<html><body>"
        "<div class='ad-slot leaderboard'>BUY NOW</div>"
        "<div class='sponsored-content'>Sponsored by Widgets Inc</div>"
        "<aside class='promo-banner'>Limited offer!</aside>"
        "<p>Fine journalism follows.</p>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "Fine journalism follows." in text
    assert "BUY NOW" not in text
    assert "Widgets Inc" not in text
    assert "Limited offer" not in text


def test_ad_like_class_names_do_not_shadow_real_content():
    html = (
        "<html><body>"
        "<div class='ad-slot leaderboard'>BUY NOW</div>"
        "<div class='road-details'>A road trip journal.</div>"
        "<p>Kept prose here.</p>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "BUY NOW" not in text
    assert "A road trip journal." in text
    assert "Kept prose here." in text


def test_newsletter_and_subscribe_removed():
    html = (
        "<html><body>"
        "<form><label>Newsletter signup</label><input name='email'></form>"
        "<div class='subscribe-box'>Subscribe for $5/month</div>"
        "<p>Article text persists.</p>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "Article text persists." in text
    assert "Subscribe" not in text
    assert "Newsletter" not in text


def test_hidden_elements_removed():
    html = (
        "<html><body>"
        "<div style='display:none'>invisible junk</div>"
        "<p hidden>hidden paragraph</p>"
        "<div aria-hidden='true'>decorative</div>"
        "<p>visible text</p>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "visible text" in text
    assert "invisible junk" not in text
    assert "hidden paragraph" not in text
    assert "decorative" not in text


def test_role_banner_navigation_removed():
    html = (
        "<html><body>"
        "<div role='banner'><span>Site header text</span></div>"
        "<div role='navigation'><a href='/menu'>TopMenu</a></div>"
        "<article><p>content only</p></article>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "content only" in text
    assert "Site header text" not in text
    assert "TopMenu" not in text


def test_main_element_preferred_and_cleaned():
    html = (
        "<html><body>"
        "<div class='sidebar'>Sidebar links here</div>"
        "<main><p>Main article paragraph one.</p><p>Paragraph two.</p></main>"
        "<div class='sidebar'>More sidebar links</div>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "Main article paragraph one." in text
    assert "Paragraph two." in text
    assert "Sidebar links" not in text


def test_comments_are_removed():
    html = (
        "<html><body>"
        "<!-- internal comment with secrets: staging-origin-3 -->"
        "<p>public text</p>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "public text" in text
    assert "staging-origin-3" not in text


def test_site_header_with_nav_removed_but_entry_header_kept():
    html = (
        "<html><body>"
        "<header class='site-header'><nav>SiteNav</nav></header>"
        "<article><header class='entry-header'><h1>Article Title</h1></header>"
        "<p>body</p></article>"
        "</body></html>"
    )
    text = extract_body(html)
    assert "Article Title" in text
    assert "SiteNav" not in text


def test_empty_page_raises():
    with pytest.raises(EmptyPageError):
        extract("<html><body><script>only</script></body></html>")
