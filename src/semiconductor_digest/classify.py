"""Keyword-based topic classification."""

from __future__ import annotations

from .models import Article, Category

GENERAL_CATEGORY_KEY = "general"


def classify(article: Article, categories: tuple[Category, ...]) -> str:
    """Return the best-matching category key for `article`.

    A source-forced category always wins. Otherwise every non-general
    category scores itself by keyword hits against the article's title and
    summary — a title hit counts double a summary-only hit — and the
    highest score wins. Ties and zero-score articles fall through to the
    ``general`` catch-all.
    """
    if article.forced_category:
        return article.forced_category

    title_lower = article.title.lower()
    haystack = f"{title_lower} {article.summary.lower()}"

    best_key, best_score = GENERAL_CATEGORY_KEY, 0
    for category in categories:
        if category.key == GENERAL_CATEGORY_KEY:
            continue
        score = sum(2 if keyword in title_lower else 1 for keyword in category.keywords if keyword in haystack)
        if score > best_score:
            best_key, best_score = category.key, score
    return best_key
