"""Error envelope and JSON logging, without a database."""

import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, configure_logging
from app.main import create_app


def test_unhandled_error_is_a_structured_500_without_internals():
    app = create_app()

    @app.get("/boom")
    def boom():
        raise RuntimeError("leaked detail C:\\secret\\path.py")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
    }
    assert "secret" not in response.text
    assert response.headers["X-Request-ID"]


def test_validation_error_uses_the_error_envelope():
    app = create_app()

    @app.get("/items/{item_id}")
    def item(item_id: int):
        return {"item_id": item_id}

    with TestClient(app) as client:
        response = client.get("/items/not-a-number")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_json_formatter_emits_one_json_object_with_extras():
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    record.request_id = "abc123"
    record.actor_id = "user-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["request_id"] == "abc123"
    assert payload["actor_id"] == "user-1"
    assert "timestamp" in payload


def test_json_formatter_drops_uvicorn_terminal_colour_duplicate():
    record = logging.LogRecord("uvicorn.error", logging.INFO, __file__, 1, "Started", (), None)
    record.color_message = "\x1b[36mStarted\x1b[0m"

    assert "color_message" not in json.loads(JsonFormatter().format(record))


def test_uvicorn_logs_go_through_json_except_its_access_log():
    configure_logging("INFO")

    assert logging.getLogger("uvicorn.error").propagate
    assert not logging.getLogger("uvicorn.error").handlers
    # The app's own request log (logger "app.request") replaces uvicorn's access log.
    access = logging.getLogger("uvicorn.access")
    assert not access.propagate
    assert not access.handlers
