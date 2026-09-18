"""Outbound email and SMS delivery.

Messages are queued to a table rather than sent inline. A slow or failing
provider must never delay a student's request or lose a notification
because the process restarted.
"""

import smtplib
from email.message import EmailMessage

from flask import current_app

from app.extensions import db
from app.models.base import utcnow
from app.models.message import OutboundMessage

MAX_ATTEMPTS = 5


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
        # No provider configured. The message stays queued rather than
        # being marked sent, so nothing is silently dropped.
        raise RuntimeError("SMTP is not configured")

    email = EmailMessage()
    email["Subject"] = message.subject or "Update on your complaint"
    email["From"] = current_app.config["MAIL_FROM"]
    email["To"] = message.recipient
    email.set_content(message.body)

    port = current_app.config.get("SMTP_PORT", 587)
    username = current_app.config.get("SMTP_USERNAME")
    password = current_app.config.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        if username:
            server.login(username, password)
        server.send_message(email)


def _send_sms(message: OutboundMessage) -> None:
    provider = current_app.config.get("SMS_PROVIDER")
    if not provider:
        raise RuntimeError("No SMS provider is configured")
    # Provider integration is deliberately left to deployment: the choice
    # differs by institution and by contract.
    raise RuntimeError(f"SMS provider '{provider}' is not implemented")


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

    for message in pending:
        message.attempts += 1
        message.last_attempt_at = utcnow()
        try:
            if message.channel == "email":
                _send_email(message)
            else:
                _send_sms(message)
            message.status = "sent"
            message.sent_at = utcnow()
            message.error = None
            sent += 1
        except Exception as error:  # noqa: BLE001 - recorded, not raised
            message.error = str(error)[:500]
            if message.attempts >= MAX_ATTEMPTS:
                message.status = "failed"
                failed += 1

    db.session.commit()
    return {"sent": sent, "failed": failed, "considered": len(pending)}
