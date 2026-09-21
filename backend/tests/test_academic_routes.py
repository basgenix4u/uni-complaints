"""The academic structure and register, over HTTP.

The tables and the import logic existed since stage 1 with no route to
reach them, which meant `verification_mode="register"` silently degraded
to manual review of every registration. These tests cover the endpoints
that close that gap, and the failure modes that matter when a registrar
uploads a real spreadsheet.
"""

import io

from app.extensions import db
from app.models.academic import AcademicDepartment, AcademicSession, Faculty, StudentRecord
from app.models.institution import Institution
from app.models.user import User
from tests.conftest import auth, login, make_institution, make_user


def admin_token(client, institution, email="vc@test.ng"):
    make_user(institution, email, role="institution_admin")
    return login(client, email)


def upload(content: str, name: str = "register.csv"):
    return {"file": (io.BytesIO(content.encode()), name)}


def session_for(client, token, name="2025/2026", current=True):
    return client.post(
        "/api/academic/sessions", headers=auth(token), json={"name": name, "is_current": current}
    )


# -- sessions ---------------------------------------------------------


def test_an_administrator_can_open_a_session(client, alpha):
    token = admin_token(client, alpha)

    response = session_for(client, token)

    assert response.status_code == 201
    assert AcademicSession.query.count() == 1


def test_only_one_session_is_current(client, alpha, db):
    """Two current sessions would make 'which intake' meaningless."""
    token = admin_token(client, alpha)
    session_for(client, token, "2024/2025")
    session_for(client, token, "2025/2026")

    current = AcademicSession.query.filter_by(is_current=True).all()
    assert len(current) == 1
    assert current[0].name == "2025/2026"


def test_a_duplicate_session_is_refused(client, alpha):
    token = admin_token(client, alpha)
    session_for(client, token)

    assert session_for(client, token).status_code == 409


def test_an_officer_cannot_open_a_session(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")

    response = client.post(
        "/api/academic/sessions",
        headers=auth(login(client, "officer@test.ng")),
        json={"name": "2025/2026"},
    )

    assert response.status_code == 403


# -- faculties and departments ----------------------------------------


def test_a_faculty_can_be_created_and_listed(client, alpha):
    token = admin_token(client, alpha)

    created = client.post(
        "/api/academic/faculties", headers=auth(token), json={"name": "Engineering"}
    )
    assert created.status_code == 201

    rows = client.get("/api/academic/faculties", headers=auth(token)).get_json()["data"]
    assert rows["faculties"][0]["slug"] == "engineering"


def test_a_department_belongs_to_a_faculty(client, alpha):
    token = admin_token(client, alpha)
    faculty_id = client.post(
        "/api/academic/faculties", headers=auth(token), json={"name": "Engineering"}
    ).get_json()["data"]["faculty"]["id"]

    created = client.post(
        f"/api/academic/faculties/{faculty_id}/departments",
        headers=auth(token),
        json={"name": "Computer Engineering"},
    )

    assert created.status_code == 201
    assert AcademicDepartment.query.first().faculty_id == faculty_id


def test_a_duplicate_faculty_is_refused(client, alpha):
    token = admin_token(client, alpha)
    client.post("/api/academic/faculties", headers=auth(token), json={"name": "Engineering"})

    again = client.post(
        "/api/academic/faculties", headers=auth(token), json={"name": "engineering"}
    )

    assert again.status_code == 409


def test_faculties_do_not_cross_institutions(client, alpha, beta):
    alpha_token = admin_token(client, alpha)
    client.post("/api/academic/faculties", headers=auth(alpha_token), json={"name": "Engineering"})

    beta_token = admin_token(client, beta, "vc@beta.ng")
    rows = client.get("/api/academic/faculties", headers=auth(beta_token)).get_json()["data"]

    assert rows["faculties"] == []


def test_the_whole_tree_can_be_imported_at_once(client, alpha):
    """A university has dozens of departments; typing them is not a product."""
    token = admin_token(client, alpha)

    response = client.post(
        "/api/academic/structure/bulk",
        headers=auth(token),
        data={
            **upload(
                "faculty,department\n"
                "Engineering,Computer Engineering\n"
                "Engineering,Civil Engineering\n"
                "Science,Microbiology\n",
                "structure.csv",
            ),
            "dry_run": "false",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    summary = response.get_json()["data"]["summary"]
    assert summary["faculties_created"] == 2
    assert summary["departments_created"] == 3
    assert Faculty.query.count() == 2


def test_a_structure_dry_run_writes_nothing(client, alpha):
    token = admin_token(client, alpha)

    response = client.post(
        "/api/academic/structure/bulk",
        headers=auth(token),
        data={**upload("faculty,department\nEngineering,Civil\n", "s.csv"), "dry_run": "true"},
        content_type="multipart/form-data",
    )

    assert response.get_json()["data"]["summary"]["faculties_created"] == 1
    assert Faculty.query.count() == 0


def test_a_structure_file_without_a_faculty_column_is_refused(client, alpha):
    token = admin_token(client, alpha)

    response = client.post(
        "/api/academic/structure/bulk",
        headers=auth(token),
        data=upload("department\nCivil\n", "s.csv"),
        content_type="multipart/form-data",
    )

    assert response.status_code == 422


# -- importing the register -------------------------------------------


REGISTER = (
    "matric_number,full_name,faculty,department,level\n"
    "ENG/COE/21/013,Amina Yusuf,Engineering,Computer Engineering,300\n"
    "ENG/CIV/22/077,Ngozi Eze,Engineering,Civil Engineering,200\n"
)


def prepared(client, alpha):
    """An institution with a session and the academic tree in place."""
    token = admin_token(client, alpha)
    session_for(client, token)
    client.post(
        "/api/academic/structure/bulk",
        headers=auth(token),
        data={
            **upload(
                "faculty,department\n"
                "Engineering,Computer Engineering\n"
                "Engineering,Civil Engineering\n",
                "s.csv",
            ),
            "dry_run": "false",
        },
        content_type="multipart/form-data",
    )
    return token


def test_the_register_can_be_imported(client, alpha):
    token = prepared(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["summary"]["created"] == 2
    assert StudentRecord.query.count() == 2


def test_a_dry_run_reports_without_writing(client, alpha):
    """A register import decides who can sign up, so it is previewed first."""
    token = prepared(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "true"},
        content_type="multipart/form-data",
    )

    assert response.get_json()["data"]["summary"]["created"] == 2
    assert StudentRecord.query.count() == 0


def test_importing_without_a_session_is_refused_with_advice(client, alpha):
    token = admin_token(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert "session" in response.get_json()["message"].lower()


def test_a_second_import_adds_rather_than_replaces(client, alpha):
    """Admissions happen every year; last year's students must survive."""
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={
            **upload("matric_number,full_name\nENG/MEC/23/001,Sade Bello\n"),
            "dry_run": "false",
        },
        content_type="multipart/form-data",
    )

    assert StudentRecord.query.count() == 3


def test_an_empty_file_is_refused(client, alpha):
    token = prepared(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(""), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422


def test_a_file_with_no_matric_column_is_refused_clearly(client, alpha):
    token = prepared(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload("full_name\nAmina Yusuf\n"), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    problems = response.get_json()["data"]["summary"]["problems"]
    assert any("matric" in p.lower() for p in problems)


def test_an_import_with_no_file_is_refused(client, alpha):
    token = prepared(client, alpha)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={"dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422


def test_an_oversized_register_is_refused_rather_than_truncated(client, alpha):
    """Silently importing half a register would be worse than refusing it."""
    token = prepared(client, alpha)
    huge = "matric_number,full_name\n" + ("ENG/COE/21/001,A Student\n" * 200_000)

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(huge), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code in (413, 422)


def test_a_non_utf8_spreadsheet_is_still_read(client, alpha):
    """Registry exports from Windows are rarely UTF-8."""
    token = prepared(client, alpha)
    latin = "matric_number,full_name\nENG/COE/21/013,Amina Yusuf\n".encode("latin-1")

    response = client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={"file": (io.BytesIO(latin), "r.csv"), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert StudentRecord.query.count() == 1


# -- the register in use ----------------------------------------------


def test_an_imported_student_is_approved_outright(client, alpha, db):
    """The whole point of the register: no administrator in the loop."""
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    alpha.verification_mode = "register"
    db.session.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Amina Yusuf",
            "email": "amina@test.ng",
            "password": "Password123",
            "institution": "alpha-university",
            "matric_number": "eng/coe/21/013",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["user"]["approval_status"] == "approved"


def test_the_summary_warns_when_no_session_is_open(client, alpha, db):
    """The first thing that blocks an import, so it is named first."""
    token = admin_token(client, alpha)
    alpha.verification_mode = "register"
    db.session.commit()

    summary = client.get(
        "/api/academic/register/summary", headers=auth(token)
    ).get_json()["data"]["summary"]

    assert summary["current_session"] is None
    assert "no session is open" in summary["advice"].lower()


def test_the_summary_warns_when_the_register_is_empty(client, alpha, db):
    """Otherwise the institution discovers it through a queue of stuck students."""
    token = admin_token(client, alpha)
    session_for(client, token)
    alpha.verification_mode = "register"
    db.session.commit()

    summary = client.get(
        "/api/academic/register/summary", headers=auth(token)
    ).get_json()["data"]["summary"]

    assert summary["total"] == 0
    assert "empty" in summary["advice"]


def test_the_summary_is_quiet_when_everything_is_in_place(client, alpha, db):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )
    alpha.verification_mode = "register"
    db.session.commit()

    summary = client.get(
        "/api/academic/register/summary", headers=auth(token)
    ).get_json()["data"]["summary"]

    assert summary["total"] == 2
    assert summary["advice"] is None


def test_the_register_can_be_searched(client, alpha):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    rows = client.get(
        "/api/academic/register?search=Ngozi", headers=auth(token)
    ).get_json()["data"]["records"]

    assert len(rows) == 1
    assert rows[0]["matric_number"] == "ENG/CIV/22/077"


def test_searching_tolerates_how_a_matric_is_typed(client, alpha):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    rows = client.get(
        "/api/academic/register?search=eng coe 21 013", headers=auth(token)
    ).get_json()["data"]["records"]

    assert len(rows) == 1


def test_a_record_can_be_corrected(client, alpha):
    """A student blocked by a typo should not wait for the next import."""
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    record = StudentRecord.query.filter_by(matric_number="ENG/COE/21/013").first()
    response = client.put(
        f"/api/academic/register/{record.id}",
        headers=auth(token),
        json={"full_name": "Aminat Yusuf", "status": "graduated"},
    )

    assert response.status_code == 200
    assert StudentRecord.query.get(record.id).full_name == "Aminat Yusuf"


def test_an_invalid_enrolment_status_is_refused(client, alpha):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    record = StudentRecord.query.first()
    response = client.put(
        f"/api/academic/register/{record.id}", headers=auth(token), json={"status": "invented"}
    )

    assert response.status_code == 422


def test_a_wrongly_claimed_record_can_be_released(client, alpha, db):
    """Otherwise the real student is locked out permanently."""
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    record = StudentRecord.query.filter_by(matric_number="ENG/COE/21/013").first()
    impostor = make_user(alpha, "impostor@test.ng")
    record.claim(impostor)
    db.session.commit()

    response = client.delete(f"/api/academic/register/{record.id}", headers=auth(token))

    assert response.status_code == 200
    assert StudentRecord.query.get(record.id).claimed_by_user_id is None


def test_releasing_an_unclaimed_record_is_refused(client, alpha):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    record = StudentRecord.query.first()
    assert client.delete(
        f"/api/academic/register/{record.id}", headers=auth(token)
    ).status_code == 409


def test_the_register_does_not_cross_institutions(client, alpha, beta):
    token = prepared(client, alpha)
    client.post(
        "/api/academic/register/import",
        headers=auth(token),
        data={**upload(REGISTER), "dry_run": "false"},
        content_type="multipart/form-data",
    )

    beta_token = admin_token(client, beta, "vc@beta.ng")
    rows = client.get(
        "/api/academic/register", headers=auth(beta_token)
    ).get_json()["data"]["records"]

    assert rows == []


def test_an_officer_cannot_read_the_register(client, alpha):
    """It is the personal data of every student at the institution."""
    make_user(alpha, "officer@test.ng", role="officer")

    response = client.get(
        "/api/academic/register", headers=auth(login(client, "officer@test.ng"))
    )

    assert response.status_code == 403
