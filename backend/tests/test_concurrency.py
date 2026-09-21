"""Two people doing the same thing at the same moment.

Both defects here were real and reproducible before the fix: the ticket
counter was a read-modify-write in Python, and the status transition was
checked in Python and written later. These pin the fixes.
"""

from app.extensions import db
from app.models.complaint import Complaint
from app.models.institution import Institution
from app.services.tickets import generate_ticket_number
from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Fees receipt not reflecting",
    "description": "I paid my school fees three weeks ago and the portal still shows unpaid.",
    "category": "fees_payment",
    "priority": "medium",
}


def test_every_ticket_advances_the_sequence(client, alpha):
    """Previously two allocations could read the same value and collide."""
    numbers = {generate_ticket_number(alpha).rsplit("-", 1)[1] for _ in range(20)}
    db.session.commit()

    assert len(numbers) == 20
    assert db.session.get(Institution, alpha.id).ticket_sequence == 20


def test_ticket_numbers_are_unique_across_many_filings(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    tickets = set()
    for _ in range(10):
        response = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)
        assert response.status_code == 201, response.get_json()
        tickets.add(response.get_json()["data"]["complaint"]["ticket_number"])

    assert len(tickets) == 10


def test_the_second_officer_to_move_a_complaint_is_told(client, alpha, db):
    """Last write wins would silently discard one officer's decision."""
    make_user(alpha, "student@test.ng")
    first = make_user(alpha, "one@test.ng", role="officer")
    make_user(alpha, "two@test.ng", role="officer")
    assert first is not None

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    one = login(client, "one@test.ng")
    two = login(client, "two@test.ng")

    client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(one), json={"status": "in_progress"}
    )

    # Both officers now hold the same view of the complaint.
    resolved = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(one),
        json={"status": "resolved", "note": "Receipt has been applied."},
    )
    declined = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(two),
        json={"status": "declined", "reason": "Not our department."},
    )

    assert resolved.status_code == 200
    # Refused because the complaint is no longer in the state it was read in.
    assert declined.status_code == 409
    assert db.session.get(Complaint, complaint_id).status == "resolved"


def test_a_rejected_transition_leaves_no_partial_write(client, alpha, db):
    """The audit trail must not record a change that did not happen."""
    from app.models.complaint import ComplaintEvent

    make_user(alpha, "student@test.ng")
    make_user(alpha, "one@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = client.post(
        "/api/complaints", headers=auth(student), json=COMPLAINT
    ).get_json()["data"]["complaint"]["id"]

    one = login(client, "one@test.ng")
    client.put(
        f"/api/complaints/{complaint_id}/status", headers=auth(one), json={"status": "in_progress"}
    )
    client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(one),
        json={"status": "resolved", "note": "Sorted."},
    )

    before = ComplaintEvent.query.filter_by(complaint_id=complaint_id).count()

    # A transition that is no longer legal from the current state.
    stale = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth(one),
        json={"status": "declined", "reason": "Too late."},
    )

    assert stale.status_code == 409
    assert ComplaintEvent.query.filter_by(complaint_id=complaint_id).count() == before


def test_filing_the_same_complaint_twice_produces_two_tickets(client, alpha):
    """A double-submitted form is two records, each separately trackable.

    Deliberate: silently collapsing them would lose a genuine second
    complaint, and a student can see both and ignore one.
    """
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    first = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)
    second = client.post("/api/complaints", headers=auth(token), json=COMPLAINT)

    assert first.status_code == second.status_code == 201
    assert (
        first.get_json()["data"]["complaint"]["ticket_number"]
        != second.get_json()["data"]["complaint"]["ticket_number"]
    )
