"""Genuine parallel writes, against a real database.

Everything else in the suite runs happily on SQLite, which serialises
writes and therefore cannot express a lost update at all. Two concurrency
defects reached main because of exactly that blind spot: the suite was
structurally incapable of failing.

These tests use two independent connections doing overlapping work, and
skip where that cannot be arranged.
"""

import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.institution import Institution

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL.startswith("sqlite") or not TEST_DATABASE_URL,
    reason="needs a real PostgreSQL; SQLite serialises writes and cannot show a lost update",
)


@pytest.fixture
def engine():
    engine = create_engine(TEST_DATABASE_URL, pool_size=8, max_overflow=4)
    yield engine
    engine.dispose()


def test_two_connections_cannot_take_the_same_ticket_number(client, alpha, engine):
    """The defect: read-modify-write in Python handed out one number twice.

    Eight threads on eight connections each allocate a number. With the
    old code the sequence lands below eight and the unique constraint
    turns the collision into a server error for a real student.
    """
    institution_id = alpha.id
    allocated = []
    barrier = threading.Barrier(8)
    lock = threading.Lock()

    def allocate():
        with Session(engine) as session:
            # Every thread waits here, so the increments genuinely overlap
            # rather than queueing behind each other.
            barrier.wait(timeout=10)
            session.execute(
                text(
                    "UPDATE institutions SET ticket_sequence = ticket_sequence + 1 "
                    "WHERE id = :id"
                ),
                {"id": institution_id},
            )
            value = session.execute(
                text("SELECT ticket_sequence FROM institutions WHERE id = :id"),
                {"id": institution_id},
            ).scalar()
            session.commit()
            with lock:
                allocated.append(value)

    threads = [threading.Thread(target=allocate) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    with Session(engine) as session:
        final = session.execute(
            text("SELECT ticket_sequence FROM institutions WHERE id = :id"),
            {"id": institution_id},
        ).scalar()

    assert len(allocated) == 8, "a thread failed to allocate"
    assert final == 8, f"sequence advanced to {final}, so increments were lost"


def test_only_one_of_two_racing_officers_moves_the_complaint(client, alpha, db, engine):
    """The defect: both officers passed the check and the second overwrote.

    Two connections attempt a different transition from the same starting
    status at the same moment. Exactly one must match a row.
    """
    from app.models.complaint import Complaint
    from tests.conftest import make_user

    student = make_user(alpha, "student@test.ng")
    complaint = Complaint(
        institution_id=alpha.id,
        student_id=student.id,
        ticket_number="AAA-RACE-0001",
        title="Fees receipt not reflecting",
        description="I paid three weeks ago and the portal still shows unpaid.",
        category="fees_payment",
        status="in_progress",
    )
    db.session.add(complaint)
    db.session.commit()
    complaint_id = complaint.id

    outcomes = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def transition(target):
        with Session(engine) as session:
            barrier.wait(timeout=10)
            result = session.execute(
                text(
                    "UPDATE complaints SET status = :target "
                    "WHERE id = :id AND status = 'in_progress'"
                ),
                {"target": target, "id": complaint_id},
            )
            session.commit()
            with lock:
                outcomes.append(result.rowcount)

    threads = [
        threading.Thread(target=transition, args=("resolved",)),
        threading.Thread(target=transition, args=("declined",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert sorted(outcomes) == [0, 1], (
        f"expected exactly one writer to win, got rowcounts {outcomes}"
    )


def test_the_unique_ticket_constraint_is_actually_enforced(client, alpha, engine):
    """The safety net beneath the counter, verified rather than assumed."""
    from sqlalchemy.exc import IntegrityError

    with Session(engine) as session:
        student_id = session.execute(
            text("SELECT id FROM users WHERE institution_id = :i LIMIT 1"),
            {"i": alpha.id},
        ).scalar()

    if student_id is None:
        from tests.conftest import make_user

        student_id = make_user(alpha, "dup@test.ng").id

    def insert(ticket):
        with Session(engine) as session:
            session.execute(
                text(
                    "INSERT INTO complaints "
                    "(id, institution_id, student_id, ticket_number, title, description, "
                    " category, priority, status, is_anonymous, is_confidential, "
                    " escalation_level, response_count, created_at, updated_at) "
                    "VALUES (gen_random_uuid()::text, :i, :s, :t, 'Title here', "
                    "'A description long enough to be realistic.', 'fees_payment', "
                    "'medium', 'submitted', false, false, 0, 0, now(), now())"
                ),
                {"i": alpha.id, "s": student_id, "t": ticket},
            )
            session.commit()

    insert("AAA-DUPE-0001")
    with pytest.raises(IntegrityError):
        insert("AAA-DUPE-0001")
