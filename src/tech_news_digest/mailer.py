"""Sends the rendered digest by email over plain SMTP.

No third-party GitHub Action and no dependency beyond the Python
standard library — `smtplib`/`email` cover this fine, and it means the
whole pipeline (fetch -> dedupe -> classify -> render -> send) runs as
one plain Python invocation. GitHub Actions' job is just to run it on a
schedule and commit the archive; it never sees the email itself.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#: Port 465 connects over implicit TLS (SMTPS) from the first byte.
#: Anything else (587 is the common case) connects in the clear and
#: upgrades with STARTTLS. Between the two, this covers every mainstream
#: SMTP provider, Gmail included.
IMPLICIT_TLS_PORT = 465


class MailError(Exception):
    """Raised when sending the digest email fails for any reason.

    Wraps whatever smtplib/socket raised (auth rejected, connection
    refused, timeout, ...) so callers have exactly one exception type
    to catch, with the original error's text preserved in the message.
    """


def send_digest_email(
    *,
    html_body: str,
    subject: str,
    server: str,
    port: int,
    username: str,
    password: str,
    recipient: str,
    from_name: str,
) -> None:
    """Send `html_body` as an HTML email `From: {from_name} <{username}>`.

    Raises `MailError` on any connection, authentication, or protocol
    failure — never lets a raw `smtplib`/`OSError` exception escape.
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{from_name} <{username}>"
    message["To"] = recipient
    message.attach(MIMEText(html_body, "html"))

    try:
        if port == IMPLICIT_TLS_PORT:
            with smtplib.SMTP_SSL(server, port, timeout=30) as smtp:
                smtp.login(username, password)
                smtp.sendmail(username, [recipient], message.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.sendmail(username, [recipient], message.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"Failed to send digest email via {server}:{port} — {exc}") from exc
