"""HTTP contract for /health, /api/v1/demo-users and /api/v1/me."""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from app.db.models import AppUser, Status
from app.db.session import get_session
from app.main import create_app
from scripts.seed_demo_data import DEMO_USERS, seed

SUBMITTER = next(u for u in DEMO_USERS if u.username == "sari.submitter")


@pytest.fixture
def seeded(session: Session) -> Session:
    seed(session)
    return session


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert body.keys() == {"error"}
    assert body["error"].keys() == {"code", "message"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_health_ok_when_database_reachable(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_database_unreachable():
    dead = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    app = create_app()

    def unreachable_session():
        with Session(dead) as session:
            yield session

    app.dependency_overrides[get_session] = unreachable_session
    with TestClient(app) as client:
        response = client.get("/health")
    assert_error(response, 503, "DATABASE_UNAVAILABLE")
    assert "127.0.0.1" not in response.text


def test_demo_users_lists_active_users_with_unit_and_roles(client: TestClient, seeded: Session):
    seeded.execute(
        update(AppUser).where(AppUser.username == "rizky.consumer").values(status=Status.INACTIVE)
    )
    response = client.get("/api/v1/demo-users")
    assert response.status_code == 200
    items = {item["username"]: item for item in response.json()["items"]}

    assert "rizky.consumer" not in items
    assert set(items) == {u.username for u in DEMO_USERS} - {"rizky.consumer"}
    sari = items[SUBMITTER.username]
    assert sari["display_name"] == SUBMITTER.display_name
    assert sari["unit"]["unit_code"] == SUBMITTER.unit_code
    assert [role["role_code"] for role in sari["roles"]] == list(SUBMITTER.roles)


def test_me_returns_the_header_user(client: TestClient, seeded: Session):
    response = client.get("/api/v1/me", headers={"X-Demo-User": SUBMITTER.username})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == SUBMITTER.username
    assert body["display_name"] == SUBMITTER.display_name
    assert body["email"] == SUBMITTER.email
    assert body["unit"]["unit_name"] == "Retail Banking"
    assert [role["role_code"] for role in body["roles"]] == ["DATA_SUBMITTER"]


def test_me_without_header_is_401(client: TestClient, seeded: Session):
    assert_error(client.get("/api/v1/me"), 401, "DEMO_USER_HEADER_MISSING")


def test_me_with_unknown_user_is_401(client: TestClient, seeded: Session):
    response = client.get("/api/v1/me", headers={"X-Demo-User": "nobody"})
    assert_error(response, 401, "DEMO_USER_UNKNOWN")


def test_me_with_inactive_user_is_401(client: TestClient, seeded: Session):
    seeded.execute(
        update(AppUser).where(AppUser.username == SUBMITTER.username).values(status=Status.INACTIVE)
    )
    response = client.get("/api/v1/me", headers={"X-Demo-User": SUBMITTER.username})
    assert_error(response, 401, "DEMO_USER_INACTIVE")


def test_unknown_route_is_a_structured_404(client: TestClient):
    assert_error(client.get("/api/v1/nope"), 404, "NOT_FOUND")


def test_every_response_carries_a_request_id(client: TestClient, seeded: Session):
    first = client.get("/api/v1/me")
    second = client.get("/api/v1/me", headers={"X-Demo-User": SUBMITTER.username})
    assert first.headers["X-Request-ID"]
    assert second.headers["X-Request-ID"]
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_request_log_carries_request_id_and_actor(
    client: TestClient, seeded: Session, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/api/v1/me", headers={"X-Demo-User": SUBMITTER.username})
    (record,) = [r for r in caplog.records if r.name == "app.request"]
    assert record.request_id == response.headers["X-Request-ID"]
    assert record.actor_id == response.json()["user_id"]
    assert record.status_code == 200
