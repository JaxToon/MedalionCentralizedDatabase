"""Streamlit shell behaviour with the API faked at the HTTP-call boundary."""

from pathlib import Path

import httpx2
import pytest
from streamlit.testing.v1 import AppTest

HOME = Path(__file__).resolve().parents[2] / "frontend" / "Home.py"
DISCLAIMER = "Synthetic demo data only — not for production banking data."

SARI = {
    "user_id": "6f1c1a52-0000-4000-8000-000000000001",
    "username": "sari.submitter",
    "display_name": "Sari Wulandari",
    "email": "sari.submitter@demo.local",
    "unit": {"unit_id": "6f1c1a52-0000-4000-8000-0000000000aa", "unit_code": "RETAIL",
             "unit_name": "Retail Banking"},
    "roles": [{"role_code": "DATA_SUBMITTER", "role_name": "Data Submitter"}],
}


def json_response(url: str, status: int, body: dict) -> httpx2.Response:
    return httpx2.Response(status, json=body, request=httpx2.Request("GET", url))


def happy_api(url: str, headers: dict) -> httpx2.Response:
    if url.endswith("/api/v1/demo-users"):
        return json_response(url, 200, {"items": [SARI]})
    if url.endswith("/api/v1/me") and headers.get("X-Demo-User") == SARI["username"]:
        return json_response(url, 200, SARI)
    raise AssertionError(f"unexpected call {url} {headers}")


class FakeApi:
    """Records the frontend's httpx2.get calls and answers them with `handler`."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.handler = happy_api

    def get(self, url: str, headers: dict | None = None, timeout: float | None = None):
        self.calls.append((url, dict(headers or {})))
        return self.handler(url, dict(headers or {}))


@pytest.fixture
def api(monkeypatch) -> FakeApi:
    fake = FakeApi()
    monkeypatch.setattr(httpx2, "get", fake.get)
    return fake


def run_home() -> AppTest:
    return AppTest.from_file(str(HOME), default_timeout=30).run()


def all_text(at: AppTest) -> str:
    return "\n".join(str(el.value) for el in [*at.markdown, *at.subheader, *at.caption, *at.info])


def test_unreachable_api_shows_disclaimer_and_a_clear_message(api):
    def refuse(url, headers):
        raise httpx2.ConnectError("connection refused")

    api.handler = refuse
    at = run_home()

    assert not at.exception
    assert at.warning[0].value == DISCLAIMER
    assert "unreachable" in at.error[0].value.lower()


def test_sidebar_offers_demo_users_and_shows_the_picked_user(api):
    at = run_home()
    assert not at.exception
    assert at.warning[0].value == DISCLAIMER
    picker = at.sidebar.selectbox[0]
    assert picker.options == ["Sari Wulandari (Retail Banking)"]

    at = picker.select(SARI["username"]).run()

    assert not at.exception
    text = all_text(at)
    assert "Sari Wulandari" in text
    assert "Retail Banking" in text
    assert "Data Submitter" in text
    url, headers = api.calls[-1]
    assert url.endswith("/api/v1/me")
    assert headers == {"X-Demo-User": SARI["username"]}


def test_api_error_on_me_is_shown_to_the_user(api):
    def reject_me(url, headers):
        if url.endswith("/api/v1/demo-users"):
            return json_response(url, 200, {"items": [SARI]})
        return json_response(
            url, 401, {"error": {"code": "DEMO_USER_INACTIVE", "message": "This demo user is inactive."}}
        )

    api.handler = reject_me
    at = run_home()
    at = at.sidebar.selectbox[0].select(SARI["username"]).run()

    assert not at.exception
    assert "This demo user is inactive." in at.error[0].value
