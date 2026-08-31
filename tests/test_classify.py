from sundry.classify import classify
from sundry.models import Article, Category

CATEGORIES = (
    Category(key="dv_uvm", title="DV", blurb="", keywords=("uvm", "formal verification"), max_items=8),
    Category(key="risc_v", title="RISC-V", blurb="", keywords=("risc-v",), max_items=8),
    Category(key="general", title="General", blurb="", keywords=(), max_items=5),
)


def _article(title="", summary="", forced_category=None):
    return Article(
        title=title,
        link="https://example.com/x",
        summary=summary,
        source="Test",
        forced_category=forced_category,
    )


def test_title_keyword_match_wins_category():
    article = _article(title="New UVM testbench released")
    assert classify(article, CATEGORIES) == "dv_uvm"


def test_no_keyword_hits_falls_back_to_general():
    article = _article(title="Fab opens in Arizona", summary="Construction news")
    assert classify(article, CATEGORIES) == "general"


def test_forced_category_overrides_keyword_scoring():
    article = _article(title="Nothing keyword-related here", forced_category="risc_v")
    assert classify(article, CATEGORIES) == "risc_v"


def test_summary_only_match_still_wins_over_no_match():
    article = _article(title="Weekly roundup", summary="a RISC-V core taped out this week")
    assert classify(article, CATEGORIES) == "risc_v"


def test_title_hit_outweighs_a_single_summary_hit_elsewhere():
    # "uvm" in the title (score 2) beats "risc-v" only in the summary (score 1)
    article = _article(title="UVM verification flow updated", summary="also mentions risc-v briefly")
    assert classify(article, CATEGORIES) == "dv_uvm"
