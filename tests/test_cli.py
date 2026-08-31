import logging
from unittest.mock import MagicMock

import pytest

from tech_news_digest.cli import main, parse_args
from tech_news_digest.mailer import MailError

# A minimal but valid config with zero sources — build_digest/fetch_all
# make no network calls at all with nothing configured to fetch (see
# fetchers/__init__.py), so tests using this run fully offline.
_EMPTY_CONFIG = """\
digest_name = "Test Digest"

[[categories]]
key = "general"
title = "General"
blurb = "Everything."
max_items = 8
keywords = []
"""


@pytest.fixture
def empty_config(tmp_path):
    path = tmp_path / "feeds.toml"
    path.write_text(_EMPTY_CONFIG, encoding="utf-8")
    return path


def test_version_flag_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])
    assert exc_info.value.code == 0
    assert "tech-news-digest" in capsys.readouterr().out


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
    with caplog.at_level(logging.ERROR, logger="tech_news_digest"):
        exit_code = main(["--config", str(missing)])
    assert exit_code == 1
    assert "Config file not found" in caplog.text
    assert "Traceback" not in caplog.text


def test_invalid_config_exits_cleanly_without_a_traceback(tmp_path, caplog):
    bad = tmp_path / "feeds.toml"
    bad.write_text('[[categories]]\nkey = "foo"\ntitle = "Foo"\n', encoding="utf-8")  # missing 'general'
    with caplog.at_level(logging.ERROR, logger="tech_news_digest"):
        exit_code = main(["--config", str(bad)])
    assert exit_code == 1
    assert "Invalid config" in caplog.text
    assert "general" in caplog.text


def test_send_email_requires_mail_credentials(empty_config, monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    html_output = tmp_path / "out.html"
    with caplog.at_level(logging.ERROR, logger="tech_news_digest"):
        exit_code = main(
            ["--config", str(empty_config), "--html-output", str(html_output), "--send-email", "--no-archive"]
        )
    assert exit_code == 1
    assert "MAIL_USERNAME" in caplog.text
    # Fails before doing any of the fetch/render work.
    assert not html_output.exists()


def test_send_email_requires_a_recipient(empty_config, monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    monkeypatch.delenv("DIGEST_RECIPIENT", raising=False)
    html_output = tmp_path / "out.html"
    with caplog.at_level(logging.ERROR, logger="tech_news_digest"):
        exit_code = main(
            ["--config", str(empty_config), "--html-output", str(html_output), "--send-email", "--no-archive"]
        )
    assert exit_code == 1
    assert "recipient" in caplog.text
    assert not html_output.exists()


def test_send_email_sends_with_recipient_flag_and_subject(empty_config, monkeypatch, tmp_path):
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    send_mock = MagicMock()
    monkeypatch.setattr("tech_news_digest.cli.send_digest_email", send_mock)

    exit_code = main(
        [
            "--config",
            str(empty_config),
            "--html-output",
            str(tmp_path / "out.html"),
            "--no-archive",
            "--no-write-cache",
            "--send-email",
            "--recipient",
            "someone@example.com",
            "--subject-prefix",
            "[PR Preview] ",
        ]
    )

    assert exit_code == 0
    send_mock.assert_called_once()
    kwargs = send_mock.call_args.kwargs
    assert kwargs["recipient"] == "someone@example.com"
    assert kwargs["username"] == "bot@example.com"
    assert kwargs["password"] == "app-password"
    assert kwargs["subject"].startswith("[PR Preview] Test Digest")
    assert "(0 new items)" in kwargs["subject"]


def test_send_email_falls_back_to_digest_recipient_env_var(empty_config, monkeypatch, tmp_path):
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    monkeypatch.setenv("DIGEST_RECIPIENT", "team@example.com")
    send_mock = MagicMock()
    monkeypatch.setattr("tech_news_digest.cli.send_digest_email", send_mock)

    exit_code = main(
        [
            "--config",
            str(empty_config),
            "--html-output",
            str(tmp_path / "out.html"),
            "--no-archive",
            "--no-write-cache",
            "--send-email",
        ]
    )

    assert exit_code == 0
    assert send_mock.call_args.kwargs["recipient"] == "team@example.com"


def test_send_email_failure_exits_cleanly_without_a_traceback(empty_config, monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    monkeypatch.setattr(
        "tech_news_digest.cli.send_digest_email",
        MagicMock(side_effect=MailError("Failed to send digest email via smtp.gmail.com:465 — boom")),
    )

    with caplog.at_level(logging.ERROR, logger="tech_news_digest"):
        exit_code = main(
            [
                "--config",
                str(empty_config),
                "--html-output",
                str(tmp_path / "out.html"),
                "--no-archive",
                "--no-write-cache",
                "--send-email",
                "--recipient",
                "someone@example.com",
            ]
        )

    assert exit_code == 1
    assert "Failed to send digest email" in caplog.text
    assert "Traceback" not in caplog.text


def test_plain_build_never_sends_email(empty_config, monkeypatch, tmp_path):
    """--send-email is opt-in — a plain build must never have this side effect."""
    send_mock = MagicMock()
    monkeypatch.setattr("tech_news_digest.cli.send_digest_email", send_mock)

    exit_code = main(
        ["--config", str(empty_config), "--html-output", str(tmp_path / "out.html"), "--no-archive", "--no-write-cache"]
    )

    assert exit_code == 0
    send_mock.assert_not_called()
