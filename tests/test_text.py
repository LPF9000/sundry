from semiconductor_digest.text import strip_html, truncate


def test_strip_html_removes_tags_and_unescapes_entities():
    assert strip_html("<p>A &amp; B</p>") == "A & B"


def test_strip_html_collapses_whitespace():
    assert strip_html("a\n\n  b") == "a b"


def test_strip_html_handles_none_and_empty():
    assert strip_html(None) == ""
    assert strip_html("") == ""


def test_truncate_leaves_short_text_untouched():
    assert truncate("short text", limit=100) == "short text"


def test_truncate_cuts_on_word_boundary_and_adds_ellipsis():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    result = truncate(text, limit=20)

    assert result.endswith("…")
    assert len(result) <= 21
    # the body (minus the ellipsis) must be a clean prefix of the original text
    assert text.startswith(result[:-1])
