import os

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db as _db
from app.models.institution import Department, Institution
from app.models.user import User


def _is_postgres() -> bool:
    return not (os.getenv("TEST_DATABASE_URL") or "sqlite").startswith("sqlite")


@pytest.fixture(scope="session")
def _schema():
    """Build the schema once when running against a real database.

    Dropping and recreating every table for each of several hundred tests
    is free on in-memory SQLite and ruinous on PostgreSQL. The tables are
    created once and the rows cleared between tests instead.
    """
    if not _is_postgres():
        yield
        return

    app = create_app("testing")
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def app(_schema):
    app = create_app("testing")
    with app.app_context():
        if _is_postgres():
            yield app
            # TRUNCATE ... CASCADE resets the tables and their sequences
            # without touching the schema. Ordering does not matter, which
            # is what makes this safe against the circular foreign key
            # between faculties and users.
            _db.session.rollback()
            tables = ", ".join(
                f'"{table.name}"' for table in reversed(_db.metadata.sorted_tables)
            )
            if tables:
                _db.session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
                _db.session.commit()
            _db.session.remove()
        else:
            _db.create_all()
            yield app
            _db.session.remove()
            _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


def make_institution(code="AAA", slug="alpha-university", name="Alpha University",
                     is_onboarded=True, verification_mode="open"):
    """Create a tenant.

    Onboarded and open by default: most tests are about an institution
    already in service, and requiring each to opt in would bury the
    subject of the test. The directory and verification tests set these
    explicitly.
    """
    institution = Institution(
        name=name,
        code=code,
        slug=slug,
        is_onboarded=is_onboarded,
        verification_mode=verification_mode,
    )
    _db.session.add(institution)
    _db.session.flush()
    department = Department(institution_id=institution.id, name="Bursary", slug="bursary")
    _db.session.add(department)
    _db.session.commit()
    return institution


def make_user(institution, email, role="student", password="Password123", matric=None,
              verified=True, approval_status="approved"):
    """Create an account.

    Verified by default, because almost every test is about what an
    established account can do. The registration and verification tests
    pass `verified=False` explicitly, so the gate is still exercised
    rather than assumed away.
    """
    from app.models.base import utcnow

    user = User(
        institution_id=institution.id if institution else None,
        full_name=f"Test {role}",
        email=email,
        role=role,
        matric_number=matric,
        email_verified_at=utcnow() if verified else None,
        approval_status=approval_status,
    )
    user.set_password(password)
    _db.session.add(user)
    _db.session.commit()
    return user


def login(client, email, password="Password123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["data"]["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def alpha(db):
    return make_institution()


@pytest.fixture
def beta(db):
    return make_institution(code="BBB", slug="beta-polytechnic", name="Beta Polytechnic")
