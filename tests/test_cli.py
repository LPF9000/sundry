import logging

import pytest

from semiconductor_digest.cli import main, parse_args


def test_version_flag_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])
    assert exc_info.value.code == 0
    assert "semiconductor-digest" in capsys.readouterr().out


def test_help_flag_exits_cleanly():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])
    assert exc_info.value.code == 0


def test_invalid_log_level_is_rejected_with_a_clean_message(capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--log-level", "not-a-real-level"])
    assert exc_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_log_level_is_case_insensitive():
    args = parse_args(["--log-level", "debug"])
    assert args.log_level == "DEBUG"


def test_missing_config_file_exits_cleanly_without_a_traceback(tmp_path, caplog):
    missing = tmp_path / "does-not-exist.toml"
    with caplog.at_level(logging.ERROR, logger="semiconductor_digest"):
        exit_code = main(["--config", str(missing)])
    assert exit_code == 1
    assert "Config file not found" in caplog.text
    assert "Traceback" not in caplog.text


def test_invalid_config_exits_cleanly_without_a_traceback(tmp_path, caplog):
    bad = tmp_path / "feeds.toml"
    bad.write_text('[[categories]]\nkey = "foo"\ntitle = "Foo"\n', encoding="utf-8")  # missing 'general'
    with caplog.at_level(logging.ERROR, logger="semiconductor_digest"):
        exit_code = main(["--config", str(bad)])
    assert exit_code == 1
    assert "Invalid config" in caplog.text
    assert "general" in caplog.text
