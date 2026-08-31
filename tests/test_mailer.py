import smtplib
from email import message_from_string
from email.header import decode_header
from unittest.mock import MagicMock

import pytest

from tech_news_digest.mailer import MailError, send_digest_email

SEND_KWARGS = {
    "html_body": "<p>hello</p>",
    "subject": "Test Digest — 2026-01-01 (3 new items)",
    "username": "bot@example.com",
    "password": "app-password",
    "recipient": "someone@example.com",
    "from_name": "Digest Bot",
}


def test_send_digest_email_uses_implicit_tls_for_port_465(monkeypatch):
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp_ssl_cls = MagicMock(return_value=smtp)
    monkeypatch.setattr("tech_news_digest.mailer.smtplib.SMTP_SSL", smtp_ssl_cls)

    send_digest_email(server="smtp.gmail.com", port=465, **SEND_KWARGS)

    smtp_ssl_cls.assert_called_once_with("smtp.gmail.com", 465, timeout=30)
    smtp.login.assert_called_once_with("bot@example.com", "app-password")
    smtp.starttls.assert_not_called()
    (from_addr, to_addrs, message_text), _kwargs = smtp.sendmail.call_args
    assert from_addr == "bot@example.com"
    assert to_addrs == ["someone@example.com"]
    assert "<p>hello</p>" in message_text

    parsed = message_from_string(message_text)
    subject_bytes, encoding = decode_header(parsed["Subject"])[0]
    subject = subject_bytes.decode(encoding or "ascii")
    assert subject == SEND_KWARGS["subject"]
    assert parsed["To"] == "someone@example.com"


def test_send_digest_email_uses_starttls_for_other_ports(monkeypatch):
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp_cls = MagicMock(return_value=smtp)
    monkeypatch.setattr("tech_news_digest.mailer.smtplib.SMTP", smtp_cls)

    send_digest_email(server="smtp.example.com", port=587, **SEND_KWARGS)

    smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=30)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("bot@example.com", "app-password")


def test_send_digest_email_wraps_auth_failure_as_mail_error(monkeypatch):
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
    monkeypatch.setattr("tech_news_digest.mailer.smtplib.SMTP_SSL", MagicMock(return_value=smtp))

    with pytest.raises(MailError, match="Username and Password not accepted"):
        send_digest_email(server="smtp.gmail.com", port=465, **SEND_KWARGS)


def test_send_digest_email_wraps_connection_failure_as_mail_error(monkeypatch):
    monkeypatch.setattr(
        "tech_news_digest.mailer.smtplib.SMTP_SSL",
        MagicMock(side_effect=ConnectionRefusedError("connection refused")),
    )

    with pytest.raises(MailError, match="smtp.gmail.com:465"):
        send_digest_email(server="smtp.gmail.com", port=465, **SEND_KWARGS)
