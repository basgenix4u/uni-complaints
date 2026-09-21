from datetime import timedelta

from app.models.message import OutboundMessage
from app.services.delivery import process_queue, queue_email
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Transcript request not processed",
    "description": "I applied for my transcript two months ago and have had no response since then.",
    "category": "transcript",
    "priority": "medium",
}


def test_routine_submission_does_not_send_an_email(client, alpha):
    """Acknowledgements stay in the application.

    Emailing every state change trains people to ignore the messages.
    """
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    client.post("/api/complaints", headers=auth(token), json=COMPLAINT)

    assert OutboundMessage.query.count() == 0


def test_reply_queues_an_email(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(officer),
        json={"message": "We have located your application and it is being processed."},
    )

    message = OutboundMessage.query.filter_by(channel="email").first()
    assert message is not None
    assert message.recipient == "student@test.ng"
    assert message.status == "pending"


def test_internal_note_does_not_email_the_student(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.post(
        f"/api/complaints/{complaint_id}/responses",
        headers=auth(officer),
        json={"message": "Chasing this with the registry quietly.", "is_internal": True},
    )

    assert OutboundMessage.query.filter_by(recipient="student@test.ng").count() == 0


def test_escalation_queues_email_for_student_and_the_handling_unit(client, alpha, db):
    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.models.institution import Department
    from app.services.routing import seed_routing, seed_units
    from app.services.sla import run_escalation_sweep

    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)
    db.session.commit()

    make_user(alpha, "student@test.ng")
    head = make_user(alpha, "head@test.ng", role="dept_head")
    head.department_id = Department.query.filter_by(
        institution_id=alpha.id, slug="registry"
    ).first().id
    db.session.commit()

    token = login(client, "student@test.ng")

    complaint_id = client.post(
        "/api/complaints", headers=auth(token), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    run_escalation_sweep()

    recipients = {m.recipient for m in OutboundMessage.query.all()}
    assert "student@test.ng" in recipients
    assert "head@test.ng" in recipients


def configure_smtp(app, monkeypatch, sender):
    """A configured provider that behaves however the test needs."""
    app.config["SMTP_HOST"] = "smtp.example.test"
    monkeypatch.setattr("app.services.delivery._send_email", sender)


def test_queue_is_retried_and_eventually_marked_failed(app, alpha, monkeypatch):
    """A provider that rejects a message is retried, then given up on."""
    from app.extensions import db

    def refuse(_message):
        raise RuntimeError("mailbox full")

    configure_smtp(app, monkeypatch, refuse)
    queue_email(alpha.id, "someone@test.ng", "Subject", "Body")
    db.session.commit()

    for _ in range(5):
        process_queue()

    message = OutboundMessage.query.first()
    assert message.attempts == 5
    assert message.status == "failed"
    assert message.error


def test_failed_messages_are_not_retried_forever(app, alpha, monkeypatch):
    from app.extensions import db

    def refuse(_message):
        raise RuntimeError("mailbox full")

    configure_smtp(app, monkeypatch, refuse)
    queue_email(alpha.id, "someone@test.ng", "Subject", "Body")
    db.session.commit()

    for _ in range(6):
        process_queue()

    # Once failed the message is left alone rather than retried endlessly.
    assert process_queue()["considered"] == 0


def test_a_missing_provider_never_burns_the_retries(app, alpha):
    """The bug this guards against locked every new student out.

    Verification depends on email. When no provider was configured the
    confirmation message failed five times and died, so by the time
    somebody set up SMTP the backlog was already unrecoverable and every
    one of those people was stuck with no way to confirm.
    """
    from app.extensions import db

    queue_email(alpha.id, "someone@test.ng", "Confirm your email address", "link")
    db.session.commit()

    for _ in range(10):
        result = process_queue()

    message = OutboundMessage.query.first()
    assert message.status == "pending"
    assert message.attempts == 0
    assert result["waiting"] == 1


def test_the_backlog_sends_once_a_provider_appears(app, alpha, monkeypatch):
    from app.extensions import db

    queue_email(alpha.id, "someone@test.ng", "Confirm your email address", "link")
    db.session.commit()
    process_queue()

    configure_smtp(app, monkeypatch, lambda _message: None)

    assert process_queue()["sent"] == 1
    assert OutboundMessage.query.first().status == "sent"


def test_writing_to_the_log_is_off_unless_asked_for(app, alpha):
    """A confirmation link is a credential, so this is never a default."""
    assert app.config.get("MAIL_TO_CONSOLE") is not True


def test_the_console_fallback_delivers_when_enabled(app, alpha):
    from app.extensions import db

    app.config["MAIL_TO_CONSOLE"] = True
    queue_email(alpha.id, "someone@test.ng", "Confirm your email address", "link")
    db.session.commit()

    assert process_queue()["sent"] == 1
    app.config["MAIL_TO_CONSOLE"] = False


def test_email_is_not_queued_without_an_address(app, alpha):
    assert queue_email(alpha.id, "", "Subject", "Body") is None
