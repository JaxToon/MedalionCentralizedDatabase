"""The Compose stack as Compose itself resolves it: nothing reachable from outside the host."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_ENV = {"POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_DB": "d"}


@pytest.fixture(scope="module")
def compose() -> dict:
    if shutil.which("docker") is None:
        pytest.skip("docker CLI not available")
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        env={**os.environ, **PLACEHOLDER_ENV},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_every_published_port_binds_to_loopback(compose: dict):
    published = [
        (name, port)
        for name, service in compose["services"].items()
        for port in service.get("ports", [])
    ]
    assert published, "expected published ports"
    for name, port in published:
        assert port.get("host_ip") == "127.0.0.1", f"{name} publishes {port} beyond loopback"


def test_project_name_comes_from_the_checkout(compose: dict):
    assert compose["name"] == ROOT.name.lower()


def test_every_service_restarts_and_is_health_checked(compose: dict):
    for name, service in compose["services"].items():
        assert service.get("restart") == "unless-stopped", name
        assert service.get("healthcheck", {}).get("test"), name


def test_database_healthcheck_probes_tcp_not_the_unix_socket(compose: dict):
    test = " ".join(compose["services"]["db"]["healthcheck"]["test"])
    assert "pg_isready" in test
    assert "-h 127.0.0.1" in test


def test_one_image_is_built_once_and_shared(compose: dict):
    services = compose["services"]
    built = [name for name, service in services.items() if "build" in service]
    assert built == ["api"]
    assert services["frontend"]["image"] == services["api"]["image"]
