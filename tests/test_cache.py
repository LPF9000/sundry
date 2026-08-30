import json
from datetime import UTC, datetime, timedelta

from semiconductor_digest.cache import SeenCache

URL = "https://example.com/article"


def test_new_cache_is_empty(tmp_path):
    cache = SeenCache(tmp_path / "seen.json")
    assert URL not in cache


def test_add_then_contains(tmp_path):
    cache = SeenCache(tmp_path / "seen.json")
    cache.add(URL)
    assert URL in cache


def test_save_persists_across_instances(tmp_path):
    path = tmp_path / "seen.json"
    cache = SeenCache(path)
    cache.add(URL)
    cache.save()

    reloaded = SeenCache(path)
    assert URL in reloaded


def test_save_prunes_entries_older_than_ttl(tmp_path):
    path = tmp_path / "seen.json"
    old_timestamp = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    path.write_text(json.dumps({URL: old_timestamp}), encoding="utf-8")

    cache = SeenCache(path, ttl_days=45)
    assert URL in cache  # still loaded initially, since it hasn't been saved yet

    cache.save()

    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert URL not in reloaded


def test_corrupt_cache_file_starts_empty_instead_of_raising(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("not valid json", encoding="utf-8")

    cache = SeenCache(path)

    assert URL not in cache
