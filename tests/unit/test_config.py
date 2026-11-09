"""Settings: resolved from the project root, pinned to the project's own database server.

Each check runs Python in a fresh subprocess so that settings are read exactly as a tool
(API, alembic, seed, pytest) would read them: from the environment plus `.env`, starting
in a directory other than the repo root.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_VARS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "LOG_LEVEL",
)
CREDENTIALS = {"POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_DB": "d"}
# Builds the engine every tool uses, without connecting, and prints where it points.
PRINT_ENGINE_TARGET = (
    "from app.db.session import get_session_factory\n"
    "url = get_session_factory().kw['bind'].url\n"
    "print(url.host, url.port)"
)


def run_python(code: str, cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if k not in SETTINGS_VARS}
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env={**clean, "PYTHONPATH": str(ROOT), **env},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_building_the_api_needs_no_database_settings():
    # From tests/, with a database setting that cannot even be parsed.
    result = run_python(
        "from app.main import create_app\ncreate_app()",
        cwd=ROOT / "tests",
        POSTGRES_PORT="not-a-number",
    )
    assert result.returncode == 0, result.stderr


def test_env_file_is_read_from_the_project_root_not_the_cwd(tmp_path: Path):
    (tmp_path / ".env").write_text("POSTGRES_HOST=elsewhere.example\nPOSTGRES_PORT=6543\n")
    result = run_python(PRINT_ENGINE_TARGET, cwd=tmp_path, **CREDENTIALS)
    assert result.returncode == 0, result.stderr
    assert "elsewhere.example" not in result.stdout


@pytest.mark.parametrize(
    "host, port",
    [("localhost", "5432"), ("127.0.0.1", "5432"), ("db", "5433"), ("db.example.com", "5433")],
)
def test_tools_refuse_any_server_but_the_projects(tmp_path: Path, host: str, port: str):
    result = run_python(
        PRINT_ENGINE_TARGET, cwd=tmp_path, POSTGRES_HOST=host, POSTGRES_PORT=port, **CREDENTIALS
    )
    assert result.returncode != 0, result.stdout
    assert "this project's database" in result.stderr


@pytest.mark.parametrize(
    "host, port", [("localhost", "5433"), ("127.0.0.1", "5433"), ("db", "5432")]
)
def test_tools_accept_the_project_server_from_the_host_and_from_compose(
    tmp_path: Path, host: str, port: str
):
    result = run_python(
        PRINT_ENGINE_TARGET, cwd=tmp_path, POSTGRES_HOST=host, POSTGRES_PORT=port, **CREDENTIALS
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [host, port]


def test_integration_fixtures_refuse_the_compose_endpoint(tmp_path: Path):
    # db:5432 is valid for the API inside Compose, but tests create and drop databases
    # and must only ever do that on localhost:5433. ("db" does not resolve on the host,
    # so even a missing guard cannot reach a real server here.)
    result = run_python(
        "from tests.integration.conftest import temporary_database\n"
        "with temporary_database():\n"
        "    pass",
        cwd=tmp_path,
        POSTGRES_HOST="db",
        POSTGRES_PORT="5432",
        **CREDENTIALS,
    )
    assert result.returncode != 0
    assert "Refusing" in result.stderr


def names_invalid_field(stderr: str, field: str) -> bool:
    """A settings validation error lists each invalid field on a line of its own."""
    return re.search(rf"^{field}$", stderr, re.M) is not None


def test_settings_errors_name_the_field_but_never_echo_its_value(tmp_path: Path):
    result = run_python(
        PRINT_ENGINE_TARGET, cwd=tmp_path, POSTGRES_PORT="s3cret-value", **CREDENTIALS
    )
    assert result.returncode != 0
    assert names_invalid_field(result.stderr, "postgres_port"), result.stderr
    assert "s3cret-value" not in result.stderr


def test_invalid_log_level_is_rejected_as_a_settings_error(tmp_path: Path):
    result = run_python("import app.main", cwd=tmp_path, LOG_LEVEL="LOUD", **CREDENTIALS)
    assert result.returncode != 0
    assert names_invalid_field(result.stderr, "log_level"), result.stderr


def test_database_url_never_falls_back_to_the_dev_database(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import DatabaseSettings

    for var in SETTINGS_VARS:
        monkeypatch.delenv(var, raising=False)
    settings = DatabaseSettings(
        _env_file=None, postgres_user="u", postgres_password="p", postgres_db="dev"
    )
    assert settings.database_url().database == "dev"
    assert settings.database_url("other").database == "other"
    assert settings.database_url("").database != "dev"
