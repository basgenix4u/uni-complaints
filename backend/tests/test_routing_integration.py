"""Routing applied at the point of filing, and what it changes.

The routing tables existed before this; nothing called them. A complaint
carried a category and a department and nothing connected the two, so
everything landed in one undifferentiated queue. These tests cover the
wiring, the confidential queue it makes possible, and the report that
catches whatever the hierarchy still ignores.
"""

from datetime import timedelta

from app.extensions import db
from app.models.base import utcnow
from app.models.complaint import Complaint
from app.models.institution import Department
from app.services.routing import seed_routing, seed_units
from tests.conftest import auth, login, make_user

FEES = {
    "title": "Fees receipt not reflecting",
    "description": "I paid my school fees three weeks ago and the portal still shows unpaid.",
    "category": "fees_payment",
    "priority": "medium",
}

HARASSMENT = {
    "title": "Reporting a member of staff",
    "description": "A lecturer in my department has been making me deeply uncomfortable.",
    "category": "security",
    "priority": "high",
}


def routed(institution):
    seed_units(institution)
    db.session.commit()
    seed_routing(institution)
    db.session.commit()


def unit(institution, slug):
    return Department.query.filter_by(institution_id=institution.id, slug=slug).first()


def file_complaint(client, token, payload=FEES):
    response = client.post("/api/complaints", headers=auth(token), json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]["complaint"]


# -- routing at the point of filing ------------------------------------


def test_a_complaint_is_routed_without_the_student_choosing(client, alpha):
    """A student who knew which office to ask would not need us."""
    routed(alpha)
    make_user(alpha, "student@test.ng")

    complaint = file_complaint(client, login(client, "student@test.ng"))

    assert complaint["department"]["slug"] == "bursary"


def test_a_student_may_still_override_the_destination(client, alpha):
    routed(alpha)
    make_user(alpha, "student@test.ng")
    library = unit(alpha, "library")

    complaint = file_complaint(
        client, login(client, "student@test.ng"), {**FEES, "department_id": library.id}
    )

    assert complaint["department"]["slug"] == "library"


def test_an_unrouted_institution_can_still_accept_complaints(client, alpha):
    """Half-configured is a normal state, not a reason to refuse a student."""
    make_user(alpha, "student@test.ng")

    complaint = file_complaint(client, login(client, "student@test.ng"))

    assert complaint["department"] is None


def test_the_rule_deadline_overrides_the_institution_default(client, alpha, db):
    routed(alpha)
    rule = unit(alpha, "bursary")
    from app.models.routing import RoutingRule

    RoutingRule.query.filter_by(institution_id=alpha.id, category="fees_payment").update(
        {"sla_hours": 4}
    )
    db.session.commit()
    assert rule is not None

    make_user(alpha, "student@test.ng")
    complaint = file_complaint(client, login(client, "student@test.ng"))

    row = db.session.get(Complaint, complaint["id"])
    # Four working hours, against a default of seventy-two.
    assert (row.resolve_due_at - row.created_at) < timedelta(hours=24)


def test_routing_is_recorded_on_the_audit_trail(client, alpha, db):
    routed(alpha)
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    complaint = file_complaint(client, login(client, "student@test.ng"))

    response = client.get(
        f"/api/complaints/{complaint['id']}", headers=auth(login(client, "officer@test.ng"))
    )
    events = response.get_json()["data"]["complaint"]["events"]

    assert any("Bursary" in (e["note"] or "") for e in events)


# -- confidential queues -----------------------------------------------


def test_a_safety_report_is_marked_confidential(client, alpha):
    routed(alpha)
    make_user(alpha, "student@test.ng")

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)

    assert complaint["is_confidential"] is True
    assert complaint["department"]["slug"] == "security"


def test_an_officer_outside_the_unit_cannot_see_a_confidential_report(client, alpha, db):
    """The point of the queue: not readable by the reported person's peers."""
    routed(alpha)
    make_user(alpha, "student@test.ng")

    outsider = make_user(alpha, "lecturer@test.ng", role="officer")
    outsider.department_id = unit(alpha, "bursary").id
    db.session.commit()

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)
    token = login(client, "lecturer@test.ng")

    assert client.get(f"/api/complaints/{complaint['id']}", headers=auth(token)).status_code == 404

    listed = client.get("/api/complaints", headers=auth(token)).get_json()["data"]["complaints"]
    assert all(c["id"] != complaint["id"] for c in listed)


def test_the_handling_unit_can_see_its_own_confidential_work(client, alpha, db):
    routed(alpha)
    make_user(alpha, "student@test.ng")

    officer = make_user(alpha, "security@test.ng", role="officer")
    officer.department_id = unit(alpha, "security").id
    db.session.commit()

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)
    token = login(client, "security@test.ng")

    assert client.get(f"/api/complaints/{complaint['id']}", headers=auth(token)).status_code == 200


def test_the_institution_head_sees_everything(client, alpha):
    """The user asked for this explicitly: the head sees all that goes on."""
    routed(alpha)
    make_user(alpha, "student@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)
    token = login(client, "vc@test.ng")

    assert client.get(f"/api/complaints/{complaint['id']}", headers=auth(token)).status_code == 200


def test_a_confidential_report_is_absent_from_another_units_totals(client, alpha, db):
    """A count is enough to tell a unit that one of its own was reported."""
    routed(alpha)
    make_user(alpha, "student@test.ng")

    outsider = make_user(alpha, "lecturer@test.ng", role="officer")
    outsider.department_id = unit(alpha, "bursary").id
    db.session.commit()

    student = login(client, "student@test.ng")
    file_complaint(client, student, HARASSMENT)
    file_complaint(client, student, FEES)

    payload = client.get(
        "/api/dashboard/overview", headers=auth(login(client, "lecturer@test.ng"))
    ).get_json()["data"]

    assert payload["overview"]["total_complaints"] == 1
    assert all(c["category"] != "security" for c in payload["recent_complaints"])


def test_a_confidential_report_cannot_be_handed_to_an_outsider(client, alpha, db):
    routed(alpha)
    make_user(alpha, "student@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")

    outsider = make_user(alpha, "lecturer@test.ng", role="officer")
    outsider.department_id = unit(alpha, "bursary").id
    db.session.commit()

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)

    response = client.put(
        f"/api/complaints/{complaint['id']}/assign",
        headers=auth(login(client, "vc@test.ng")),
        json={"assigned_to_id": outsider.id},
    )

    assert response.status_code == 422


def test_escalation_does_not_widen_a_confidential_audience(client, alpha, db):
    """Being ignored must not turn a private report into a public one."""
    from app.models.complaint import Notification
    from app.services.sla import run_escalation_sweep

    routed(alpha)
    make_user(alpha, "student@test.ng")

    outsider = make_user(alpha, "registrar@test.ng", role="dept_head")
    outsider.department_id = unit(alpha, "student-affairs").id
    db.session.commit()

    complaint = file_complaint(client, login(client, "student@test.ng"), HARASSMENT)
    row = db.session.get(Complaint, complaint["id"])
    row.resolve_due_at = utcnow() - timedelta(hours=1)
    db.session.commit()

    run_escalation_sweep()

    # Student Affairs is the escalation unit for a safety matter, but its
    # head is not in the handling unit and may not read the report.
    assert Notification.query.filter_by(user_id=outsider.id, type="escalation").count() == 0


# -- routing configuration ---------------------------------------------


def test_an_administrator_can_change_where_a_category_goes(client, alpha):
    routed(alpha)
    make_user(alpha, "vc@test.ng", role="institution_admin")
    token = login(client, "vc@test.ng")

    library = unit(alpha, "library")
    response = client.post(
        "/api/routing/rules",
        headers=auth(token),
        json={"category": "fees_payment", "target_type": "unit", "department_id": library.id},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["rule"]["department"] == "Library"

    make_user(alpha, "student@test.ng")
    complaint = file_complaint(client, login(client, "student@test.ng"))
    assert complaint["department"]["slug"] == "library"


def test_an_officer_cannot_change_routing(client, alpha):
    routed(alpha)
    make_user(alpha, "officer@test.ng", role="officer")

    response = client.get("/api/routing/rules", headers=auth(login(client, "officer@test.ng")))

    assert response.status_code == 403


def test_routing_cannot_be_pointed_at_another_institutions_unit(client, alpha, beta):
    routed(alpha)
    routed(beta)
    make_user(alpha, "vc@test.ng", role="institution_admin")

    response = client.post(
        "/api/routing/rules",
        headers=auth(login(client, "vc@test.ng")),
        json={
            "category": "fees_payment",
            "target_type": "unit",
            "department_id": unit(beta, "library").id,
        },
    )

    assert response.status_code == 422


def test_seeding_is_safe_to_repeat(client, alpha):
    make_user(alpha, "vc@test.ng", role="institution_admin")
    token = login(client, "vc@test.ng")

    first = client.post("/api/routing/seed", headers=auth(token)).get_json()["data"]
    second = client.post("/api/routing/seed", headers=auth(token)).get_json()["data"]

    assert first["rules_created"] > 0
    assert second["units_created"] == 0
    assert second["rules_created"] == 0


def test_a_new_institution_is_provisioned_with_working_routing(client, db):
    """Complaints should reach the right office from the first day."""
    from app.models.routing import RoutingRule

    make_user(None, "platform@test.ng", role="platform_admin")
    token = login(client, "platform@test.ng")

    response = client.post(
        "/api/platform/institutions",
        headers=auth(token),
        json={
            "name": "Gamma University",
            "code": "GAM",
            "slug": "gamma-university",
            "admin_name": "Gamma Administrator",
            "admin_email": "admin@gamma.test.ng",
            "admin_password": "Password123",
        },
    )

    assert response.status_code == 201
    institution_id = response.get_json()["data"]["institution"]["id"]
    assert RoutingRule.query.filter_by(institution_id=institution_id).count() > 0


# -- the ignored report -------------------------------------------------


def ignored_complaint(institution, student, ticket, days_ago=14):
    complaint = Complaint(
        institution_id=institution.id,
        student_id=student.id,
        ticket_number=ticket,
        title="Nobody has looked at this",
        description="Raised a long time ago and still nothing has happened since.",
        category="fees_payment",
        priority="urgent",
        status="submitted",
        escalated_at=utcnow() - timedelta(days=days_ago),
    )
    db.session.add(complaint)
    db.session.commit()
    return complaint


def test_the_institution_head_can_see_what_has_been_ignored(client, alpha):
    student = make_user(alpha, "student@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")
    ignored_complaint(alpha, student, "AAA-IGN-0001")

    response = client.get("/api/routing/ignored", headers=auth(login(client, "vc@test.ng")))

    assert response.status_code == 200
    assert response.get_json()["data"]["count"] == 1


def test_the_head_is_emailed_the_ignored_list(client, alpha, db):
    from app.models.message import OutboundMessage
    from app.services.routing import report_ignored

    student = make_user(alpha, "student@test.ng")
    head = make_user(alpha, "vc@test.ng", role="institution_admin")
    ignored_complaint(alpha, student, "AAA-IGN-0002")

    result = report_ignored(alpha, days=7)

    assert result["ignored"] == 1
    assert result["notified"] == 1
    assert OutboundMessage.query.filter_by(recipient=head.email).count() == 1


def test_an_institution_with_nothing_ignored_is_not_emailed(client, alpha):
    from app.models.message import OutboundMessage
    from app.services.routing import report_ignored

    make_user(alpha, "vc@test.ng", role="institution_admin")

    assert report_ignored(alpha, days=7)["ignored"] == 0
    assert OutboundMessage.query.count() == 0


def test_the_report_is_weekly_not_every_sweep(client, alpha, db):
    """The scheduler fires every quarter of an hour; the report must not."""
    from app.models.message import OutboundMessage
    from app.services.routing import report_ignored_everywhere

    student = make_user(alpha, "student@test.ng")
    make_user(alpha, "vc@test.ng", role="institution_admin")
    ignored_complaint(alpha, student, "AAA-IGN-0003")

    assert report_ignored_everywhere()["institutions_reported"] == 1
    assert report_ignored_everywhere()["institutions_reported"] == 0
    assert OutboundMessage.query.count() == 1


def test_the_platform_sees_which_institutions_are_not_answering(client, alpha, beta):
    """Nobody inside an institution is going to raise this."""
    student = make_user(alpha, "student@test.ng")
    make_user(None, "platform@test.ng", role="platform_admin")
    ignored_complaint(alpha, student, "AAA-IGN-0004")

    response = client.get(
        "/api/platform/ignored", headers=auth(login(client, "platform@test.ng"))
    )

    assert response.status_code == 200
    rows = response.get_json()["data"]["institutions"]
    assert len(rows) == 1
    assert rows[0]["count"] == 1
    # Ticket numbers only: the platform learns that students are waiting,
    # not what they wrote.
    assert rows[0]["tickets"] == ["AAA-IGN-0004"]


def test_an_institution_head_cannot_read_the_platform_report(client, alpha):
    make_user(alpha, "vc@test.ng", role="institution_admin")

    response = client.get("/api/platform/ignored", headers=auth(login(client, "vc@test.ng")))

    assert response.status_code == 403
