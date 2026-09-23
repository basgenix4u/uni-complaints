"""Academic structure, the student register and routing.

The demo modelled a university as one flat list of departments, which
could not express the difference between a fee complaint going to Bursary
and a grade dispute going to the student's own department. These cover
the structure that replaces it.
"""

from app.extensions import db
from app.models.academic import AcademicDepartment, AcademicSession, Faculty, StudentRecord
from app.models.institution import Department
from app.services.register import import_register, normalise_matric
from app.services.routing import resolve_destination, seed_routing, seed_units
from tests.conftest import make_user


def session_for(institution, name="2025/2026"):
    record = AcademicSession(institution_id=institution.id, name=name, is_current=True)
    db.session.add(record)
    db.session.commit()
    return record


def faculty_for(institution, name="Engineering", slug="engineering"):
    record = Faculty(institution_id=institution.id, name=name, slug=slug)
    db.session.add(record)
    db.session.commit()
    return record


def department_for(institution, faculty, name="Computer Engineering", slug="computer-engineering"):
    record = AcademicDepartment(
        institution_id=institution.id, faculty_id=faculty.id, name=name, slug=slug
    )
    db.session.add(record)
    db.session.commit()
    return record


# -- matriculation numbers --------------------------------------------


def test_matric_formats_are_normalised_before_comparison():
    """The same number is written inconsistently even within one registry."""
    for written in ("ENG/COE/21/013", "eng-coe-21-013", "ENG COE 21 013", "eng.coe.21.013"):
        assert normalise_matric(written) == "ENG/COE/21/013"


def test_other_institutions_formats_survive_normalisation():
    """Formats differ widely, so nothing may assume one shape."""
    assert normalise_matric("U19CS1001") == "U19CS1001"
    assert normalise_matric("2019/1/12345CS") == "2019/1/12345CS"


# -- the register -----------------------------------------------------


def csv_bytes(rows: str) -> bytes:
    return rows.strip().encode()


def test_a_register_is_imported(client, alpha):
    session = session_for(alpha)
    faculty = faculty_for(alpha)
    department_for(alpha, faculty)

    result = import_register(
        alpha,
        session,
        csv_bytes(
            """
matric_number,full_name,faculty,department,programme,level
ENG/COE/21/013,Amina Yusuf,Engineering,Computer Engineering,B.Eng Computer Engineering,400
ENG/COE/21/014,Chidi Okafor,Engineering,Computer Engineering,B.Eng Computer Engineering,400
"""
        ),
    )

    assert result["created"] == 2
    assert StudentRecord.query.count() == 2

    record = StudentRecord.query.filter_by(matric_number="ENG/COE/21/013").first()
    assert record.level == 400
    assert record.academic_department.name == "Computer Engineering"


def test_a_dry_run_changes_nothing(client, alpha):
    """An administrator should see what a file does before it does it."""
    session = session_for(alpha)

    result = import_register(
        alpha,
        session,
        csv_bytes("matric_number,full_name\nENG/COE/21/013,Amina Yusuf"),
        dry_run=True,
    )

    assert result["created"] == 1
    assert StudentRecord.query.count() == 0


def test_a_later_session_adds_rather_than_replaces(client, alpha):
    """Admissions happen every session, so imports accumulate."""
    first = session_for(alpha, "2024/2025")
    import_register(alpha, first, csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Amina Yusuf"))

    second = session_for(alpha, "2025/2026")
    result = import_register(alpha, second, csv_bytes(
        "matric_number,full_name\nENG/COE/22/001,New Intake"))

    assert result["created"] == 1
    # The earlier student is still there.
    assert StudentRecord.query.count() == 2


def test_a_returning_student_is_progressed_not_duplicated(client, alpha):
    session = session_for(alpha)
    import_register(alpha, session, csv_bytes(
        "matric_number,full_name,level\nENG/COE/21/013,Amina Yusuf,300"))

    result = import_register(alpha, session, csv_bytes(
        "matric_number,full_name,level\nENG/COE/21/013,Amina Yusuf,400"))

    assert result["updated"] == 1
    assert StudentRecord.query.count() == 1
    assert StudentRecord.query.first().level == 400


def test_an_import_never_reassigns_a_claimed_record(client, alpha):
    """Once someone has registered against a row, that link stands."""
    session = session_for(alpha)
    import_register(alpha, session, csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Amina Yusuf"))

    user = make_user(alpha, "amina@test.ng")
    record = StudentRecord.query.first()
    record.claim(user)
    db.session.commit()

    import_register(alpha, session, csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Someone Else"))

    assert StudentRecord.query.first().claimed_by_user_id == user.id


def test_a_file_without_the_required_columns_is_refused(client, alpha):
    session = session_for(alpha)

    result = import_register(alpha, session, csv_bytes("name,level\nAmina,400"))

    assert result["created"] == 0
    assert any("matric_number" in p for p in result["problems"])


def test_rows_missing_a_matric_number_are_reported(client, alpha):
    session = session_for(alpha)

    result = import_register(alpha, session, csv_bytes(
        "matric_number,full_name\n,No Matric\nENG/COE/21/013,Amina Yusuf"))

    assert result["created"] == 1
    assert any("Row 2" in p for p in result["problems"])


def test_an_unknown_faculty_is_reported_rather_than_invented(client, alpha):
    session = session_for(alpha)

    result = import_register(alpha, session, csv_bytes(
        "matric_number,full_name,faculty\nENG/COE/21/013,Amina Yusuf,Astrology"))

    assert any("Astrology" in p for p in result["problems"])


def test_registers_do_not_cross_institutions(client, alpha, beta):
    import_register(alpha, session_for(alpha), csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Alpha Student"))
    import_register(beta, session_for(beta), csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Beta Student"))

    # The same matriculation number exists at both, independently.
    assert StudentRecord.query.filter_by(institution_id=alpha.id).count() == 1
    assert StudentRecord.query.filter_by(institution_id=beta.id).count() == 1


# -- eligibility ------------------------------------------------------


def test_only_an_active_unclaimed_record_may_be_claimed(client, alpha):
    session = session_for(alpha)
    import_register(alpha, session, csv_bytes(
        "matric_number,full_name,status\nENG/COE/21/013,Amina Yusuf,active"))

    record = StudentRecord.query.first()
    assert record.can_register is True

    record.status = "graduated"
    db.session.commit()
    assert record.can_register is False


def test_a_claimed_record_cannot_be_claimed_again(client, alpha):
    """Stops two people registering as the same student."""
    session = session_for(alpha)
    import_register(alpha, session, csv_bytes(
        "matric_number,full_name\nENG/COE/21/013,Amina Yusuf"))

    record = StudentRecord.query.first()
    record.claim(make_user(alpha, "first@test.ng"))
    db.session.commit()

    assert record.can_register is False


# -- routing ----------------------------------------------------------


def test_the_default_units_are_created(client, alpha):
    # The fixture already creates Bursary, so that one is skipped rather
    # than duplicated.
    created = seed_units(alpha)
    db.session.commit()

    assert created == 10
    slugs = {d.slug for d in Department.query.filter_by(institution_id=alpha.id).all()}
    assert {"bursary", "registry", "student-affairs", "sug", "ict"} <= slugs


def test_seeding_units_twice_creates_nothing_extra(client, alpha):
    seed_units(alpha)
    db.session.commit()
    again = seed_units(alpha)
    db.session.commit()

    assert again == 0


def test_a_fee_complaint_routes_to_bursary(client, alpha):
    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)

    student = make_user(alpha, "student@test.ng")
    destination, rule = resolve_destination(alpha, "fees_payment", student)

    assert destination is not None
    assert destination.slug == "bursary"
    assert rule.target_type == "unit"


def test_an_academic_complaint_routes_to_the_students_own_department(client, alpha):
    """The destination depends on who is complaining, not the category."""
    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)

    faculty = faculty_for(alpha)
    department_for(alpha, faculty, "Computer Engineering", "computer-engineering")
    db.session.add(
        Department(
            institution_id=alpha.id, name="Computer Engineering", slug="computer-engineering"
        )
    )
    db.session.commit()

    student = make_user(alpha, "student@test.ng")
    import_register(alpha, session_for(alpha), csv_bytes(
        "matric_number,full_name,faculty,department\n"
        "ENG/COE/21/013,Amina Yusuf,Engineering,Computer Engineering"))
    record = StudentRecord.query.first()
    record.claim(student)
    db.session.commit()

    destination, rule = resolve_destination(alpha, "course_registration", student)

    assert rule.target_type == "department"
    assert destination.slug == "computer-engineering"


def test_safety_complaints_are_confidential_by_default(client, alpha):
    """Getting this wrong is a safeguarding failure, not a routing error."""
    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)

    student = make_user(alpha, "student@test.ng")
    _, rule = resolve_destination(alpha, "security", student)

    assert rule.is_confidential is True


def test_an_unrouted_category_does_not_block_filing(client, alpha):
    """An institution mid-setup must still be able to accept complaints."""
    seed_units(alpha)
    db.session.commit()

    student = make_user(alpha, "student@test.ng")
    destination, rule = resolve_destination(alpha, "fees_payment", student)

    assert destination is None
    assert rule is None


def test_routing_does_not_cross_institutions(client, alpha, beta):
    seed_units(alpha)
    db.session.commit()
    seed_routing(alpha)

    student = make_user(beta, "beta@test.ng")
    destination, rule = resolve_destination(beta, "fees_payment", student)

    assert destination is None
    assert rule is None


# -- ignored complaints -----------------------------------------------


def test_ignored_complaints_are_surfaced_for_the_institution_head(client, alpha, db):
    """Escalation raises to unit heads; this is the layer above."""
    from datetime import timedelta

    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.services.routing import ignored_complaints

    student = make_user(alpha, "student@test.ng")
    complaint = Complaint(
        institution_id=alpha.id,
        student_id=student.id,
        ticket_number="AAA-TEST-0001",
        title="Ignored for a fortnight",
        description="Nobody has looked at this since it was raised.",
        category="fees_payment",
        priority="high",
        status="submitted",
        escalated_at=utcnow() - timedelta(days=14),
    )
    db.session.add(complaint)
    db.session.commit()

    assert len(ignored_complaints(alpha, days=7)) == 1
    # Recently escalated work is not yet ignored.
    assert len(ignored_complaints(alpha, days=30)) == 0


def test_resolved_work_is_never_reported_as_ignored(client, alpha, db):
    from datetime import timedelta

    from app.models.base import utcnow
    from app.models.complaint import Complaint
    from app.services.routing import ignored_complaints

    student = make_user(alpha, "student@test.ng")
    db.session.add(
        Complaint(
            institution_id=alpha.id,
            student_id=student.id,
            ticket_number="AAA-TEST-0002",
            title="Escalated then resolved",
            description="This was escalated but has since been dealt with.",
            category="fees_payment",
            priority="high",
            status="resolved",
            escalated_at=utcnow() - timedelta(days=20),
        )
    )
    db.session.commit()

    assert ignored_complaints(alpha, days=7) == []
