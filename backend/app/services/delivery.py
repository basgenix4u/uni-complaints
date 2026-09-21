"""Outbound email and SMS delivery.

Messages are queued to a table rather than sent inline. A slow or failing
provider must never delay a student's request or lose a notification
because the process restarted.
"""

import smtplib
from email.message import EmailMessage

import structlog
from flask import current_app

from app.extensions import db
from app.models.base import utcnow
from app.models.message import OutboundMessage

MAX_ATTEMPTS = 5


class NotConfigured(Exception):
    """No provider is set up for this channel.

    Distinct from a delivery failure on purpose. A provider that rejects
    a message has told us something about that message, and retrying is
    worth a few attempts before giving up. A provider that does not exist
    says nothing about the message at all, and burning its retries means
    that when someone finally configures SMTP, the backlog is already
    dead and every one of those people is locked out.
    """


def queue_email(institution_id: str, to_address: str, subject: str, body: str,
                user_id: str | None = None, complaint_id: str | None = None):
    if not to_address:
        return None
    message = OutboundMessage(
        institution_id=institution_id,
        user_id=user_id,
        complaint_id=complaint_id,
        channel="email",
        recipient=to_address,
        subject=subject[:200],
        body=body,
    )
    db.session.add(message)
    return message


def queue_sms(institution_id: str, to_number: str, body: str,
              user_id: str | None = None, complaint_id: str | None = None):
    """Queue a text message.

    Kept short deliberately: SMS is charged per segment, and for many
    users a text is the only notification that reaches them reliably.
    """
    if not to_number:
        return None
    message = OutboundMessage(
        institution_id=institution_id,
        user_id=user_id,
        complaint_id=complaint_id,
        channel="sms",
        recipient=to_number,
        body=body[:320],
    )
    db.session.add(message)
    return message


def _send_email(message: OutboundMessage) -> None:
    host = current_app.config.get("SMTP_HOST")

    if not host:
        # A deliberate escape for local work and for a first deployment
        # where SMTP is not ready: write the message to the log so the
        # confirmation link can be read and used. Never enabled by
        # default, and refused outright in production, because it puts
        # account-confirmation links into the log stream.
        if current_app.config.get("MAIL_TO_CONSOLE"):
            structlog.get_logger().warning(
                "email_written_to_log",
                to=message.recipient,
                subject=message.subject,
                body=message.body,
            )
            return
        raise NotConfigured("SMTP is not configured")

    email = EmailMessage()
    email["Subject"] = message.subject or "Update on your complaint"
    email["From"] = current_app.config["MAIL_FROM"]
    email["To"] = message.recipient
    email.set_content(message.body)

    port = current_app.config.get("SMTP_PORT", 587)
    username = current_app.config.get("SMTP_USERNAME")
    password = current_app.config.get("SMTP_PASSWORD")

    # Port 465 is implicit TLS: the connection is encrypted from the
    # first byte and STARTTLS is never sent. 587 is the reverse. Calling
    # starttls() unconditionally, as this did, fails against both 465 and
    # any relay that does not advertise it.
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            if username:
                server.login(username, password)
            server.send_message(email)
        return

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        if server.has_extn("starttls"):
            server.starttls()
            server.ehlo()
        elif username:
            # Sending a password over a connection in the clear is worse
            # than not sending the message.
            raise RuntimeError(
                f"{host}:{port} does not offer STARTTLS, so the credentials would be "
                "sent in the clear. Use port 465, or a relay that supports STARTTLS."
            )

        if username:
            server.login(username, password)
        server.send_message(email)


def _send_sms(message: OutboundMessage) -> None:
    from app.services.sms import send

    if not current_app.config.get("SMS_PROVIDER"):
        raise NotConfigured("No SMS provider is configured")

    send(message.recipient, message.body)


def process_queue(limit: int = 100) -> dict:
    """Attempt delivery of pending messages.

    Each message is retried up to a fixed number of times, after which it
    is marked failed and left for inspection rather than retried forever.
    """
    pending = (
        OutboundMessage.query.filter(
            OutboundMessage.status == "pending",
            OutboundMessage.attempts < MAX_ATTEMPTS,
        )
        .order_by(OutboundMessage.created_at)
        .limit(limit)
        .all()
    )

    sent = 0
    failed = 0
    waiting = 0
    retrying = 0

    for message in pending:
        try:
            if message.channel == "email":
                _send_email(message)
            else:
                _send_sms(message)
        except NotConfigured as error:
            # Left exactly as it was, attempt count untouched. The
            # message is waiting on a deployment step, not failing, and
            # it must still be deliverable once that step is done.
            message.error = str(error)[:500]
            waiting += 1
            continue
        except Exception as error:  # noqa: BLE001 - recorded, not raised
            message.attempts += 1
            message.last_attempt_at = utcnow()
            message.error = str(error)[:500]
            if message.attempts >= MAX_ATTEMPTS:
                message.status = "failed"
                failed += 1
            else:
                retrying += 1
            continue

        message.attempts += 1
        message.last_attempt_at = utcnow()
        message.status = "sent"
        message.sent_at = utcnow()
        message.error = None
        sent += 1

    db.session.commit()
    return {
        "sent": sent,
        "failed": failed,
        "retrying": retrying,
        "waiting": waiting,
        "considered": len(pending),
    }
