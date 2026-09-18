import pytest

from app import create_app
from app.extensions import db as _db
from app.models.institution import Department, Institution
from app.models.user import User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
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


def make_institution(code="AAA", slug="alpha-university", name="Alpha University"):
    institution = Institution(name=name, code=code, slug=slug)
    _db.session.add(institution)
    _db.session.flush()
    department = Department(institution_id=institution.id, name="Bursary", slug="bursary")
    _db.session.add(department)
    _db.session.commit()
    return institution


def make_user(institution, email, role="student", password="Password123", matric=None):
    user = User(
        institution_id=institution.id if institution else None,
        full_name=f"Test {role}",
        email=email,
        role=role,
        matric_number=matric,
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
