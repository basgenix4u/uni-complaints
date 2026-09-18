import pytest

from app.models.message import OutboundMessage
from app.services import sms
from app.services.delivery import process_queue, queue_sms
from tests.conftest import auth, login, make_user


def test_no_provider_configured_is_an_error(app):
    with pytest.raises(sms.SmsError, match="No SMS provider"):
        sms.send("+2348012345678", "Test")


def test_unknown_provider_names_the_supported_ones(app):
    app.config["SMS_PROVIDER"] = "carrier-pigeon"

    with pytest.raises(sms.SmsError, match="termii"):
        sms.send("+2348012345678", "Test")


def test_console_provider_accepts_a_message(app):
    """Lets the queue be exercised without a provider account."""
    app.config["SMS_PROVIDER"] = "console"

    assert sms.send("+2348012345678", "Test")["status"] == "logged"


def test_termii_requires_its_key(app):
    app.config["SMS_PROVIDER"] = "termii"
    app.config["TERMII_API_KEY"] = None

    with pytest.raises(sms.SmsError, match="TERMII_API_KEY"):
        sms.send("+2348012345678", "Test")


def test_africastalking_requires_both_credentials(app):
    app.config["SMS_PROVIDER"] = "africastalking"
    app.config["AFRICASTALKING_API_KEY"] = "key"
    app.config["AFRICASTALKING_USERNAME"] = None

    with pytest.raises(sms.SmsError, match="AFRICASTALKING"):
        sms.send("+2348012345678", "Test")


def test_queued_text_is_sent_through_the_configured_provider(app, alpha):
    from app.extensions import db

    app.config["SMS_PROVIDER"] = "console"
    queue_sms(alpha.id, "+2348012345678", "Your complaint was escalated.")
    db.session.commit()

    result = process_queue()

    assert result["sent"] == 1
    assert OutboundMessage.query.first().status == "sent"


def test_text_is_not_queued_without_a_number(app, alpha):
    assert queue_sms(alpha.id, "", "Body") is None


def test_escalation_texts_a_student_who_has_a_number(client, alpha, db):
    """Escalation is the one event worth the cost of a text."""
    from datetime import timedelta

    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.services.sla import run_escalation_sweep

    student = make_user(alpha, "student@test.ng")
    student.phone = "+2348012345678"
    make_user(alpha, "head@test.ng", role="dept_head")
    db.session.commit()

    token = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints",
        headers=auth(token),
        json={
            "title": "Fees receipt not reflecting",
            "description": "I paid three weeks ago and the portal still shows my fees as unpaid.",
            "category": "fees_payment",
            "priority": "medium",
        },
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    run_escalation_sweep()

    text = OutboundMessage.query.filter_by(channel="sms").first()
    assert text is not None
    assert text.recipient == "+2348012345678"
    assert complaint.ticket_number in text.body


def test_no_text_when_the_student_has_no_number(client, alpha, db):
    from datetime import timedelta

    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.services.sla import run_escalation_sweep

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint_id = client.post(
        "/api/complaints",
        headers=auth(token),
        json={
            "title": "Library access card not working",
            "description": "My card has stopped opening the library turnstile since last week.",
            "category": "library",
            "priority": "low",
        },
    ).get_json()["data"]["complaint"]["id"]

    complaint = db.session.get(Complaint, complaint_id)
    complaint.resolve_due_at = utcnow() - timedelta(hours=2)
    db.session.commit()

    run_escalation_sweep()

    assert OutboundMessage.query.filter_by(channel="sms").count() == 0
