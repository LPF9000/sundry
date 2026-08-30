from pathlib import Path

import pytest

from semiconductor_digest.config import ConfigError, load_config

REPO_CONFIG = Path(__file__).resolve().parent.parent / "config" / "feeds.toml"


def test_real_config_loads_and_has_a_general_category():
    config = load_config(REPO_CONFIG)
    keys = {category.key for category in config.categories}
    assert "general" in keys
    assert config.rss_sources
    assert config.arxiv_sources
    assert config.hn_queries


def test_every_rss_default_category_is_a_real_category():
    config = load_config(REPO_CONFIG)
    category_keys = {category.key for category in config.categories}
    for source in config.rss_sources:
        if source.default_category:
            assert source.default_category in category_keys


def test_missing_general_category_is_rejected(tmp_path):
    bad = tmp_path / "feeds.toml"
    bad.write_text('[[categories]]\nkey = "foo"\ntitle = "Foo"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_duplicate_category_keys_are_rejected(tmp_path):
    bad = tmp_path / "feeds.toml"
    bad.write_text(
        '[[categories]]\nkey = "general"\ntitle = "A"\n\n[[categories]]\nkey = "general"\ntitle = "B"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_unknown_default_category_is_rejected(tmp_path):
    bad = tmp_path / "feeds.toml"
    bad.write_text(
        '[[categories]]\nkey = "general"\ntitle = "A"\n\n'
        '[[rss_sources]]\nname = "X"\nurl = "https://example.com/feed"\n'
        'default_category = "does_not_exist"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)
