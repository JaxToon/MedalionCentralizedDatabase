"""Header -> user resolution and role checks, without a database."""

import pytest

from app.api.dependencies import require_roles
from app.core.errors import AppError, ErrorCode
from app.core.security import RoleCode, authenticate_demo_user, ensure_any_role
from app.db.models import AppUser, Role, Status


def make_user(username: str = "sari.submitter", status: str = Status.ACTIVE, roles=()) -> AppUser:
    return AppUser(
        username=username,
        status=status,
        roles=[Role(role_code=code, role_name=code.title()) for code in roles],
    )


class FakeDirectory:
    """Stands in for the username lookup and records what was asked."""

    def __init__(self, *users: AppUser) -> None:
        self.users = {user.username: user for user in users}
        self.lookups: list[str] = []

    def __call__(self, username: str) -> AppUser | None:
        self.lookups.append(username)
        return self.users.get(username)


def assert_app_error(excinfo: pytest.ExceptionInfo[AppError], status: int, code: ErrorCode) -> None:
    assert excinfo.value.status_code == status
    assert excinfo.value.code == code


@pytest.mark.parametrize("header", [None, "", "   "])
def test_missing_header_is_rejected_without_lookup(header):
    directory = FakeDirectory(make_user())
    with pytest.raises(AppError) as excinfo:
        authenticate_demo_user(header, directory)
    assert_app_error(excinfo, 401, ErrorCode.DEMO_USER_HEADER_MISSING)
    assert directory.lookups == []


def test_unknown_user_is_rejected():
    with pytest.raises(AppError) as excinfo:
        authenticate_demo_user("nobody", FakeDirectory(make_user()))
    assert_app_error(excinfo, 401, ErrorCode.DEMO_USER_UNKNOWN)


def test_inactive_user_is_rejected():
    directory = FakeDirectory(make_user(status=Status.INACTIVE))
    with pytest.raises(AppError) as excinfo:
        authenticate_demo_user("sari.submitter", directory)
    assert_app_error(excinfo, 401, ErrorCode.DEMO_USER_INACTIVE)


def test_active_user_is_resolved_and_header_is_trimmed():
    user = make_user()
    directory = FakeDirectory(user)
    assert authenticate_demo_user("  sari.submitter ", directory) is user
    assert directory.lookups == ["sari.submitter"]


def test_ensure_any_role_accepts_a_matching_role():
    user = make_user(roles=[RoleCode.DATA_STEWARD])
    ensure_any_role(user, {RoleCode.DATA_STEWARD, RoleCode.PLATFORM_ADMIN})


def test_ensure_any_role_rejects_when_no_role_matches():
    user = make_user(roles=[RoleCode.DATA_CONSUMER])
    with pytest.raises(AppError) as excinfo:
        ensure_any_role(user, {RoleCode.PLATFORM_ADMIN})
    assert_app_error(excinfo, 403, ErrorCode.FORBIDDEN)


def test_require_roles_dependency_returns_an_allowed_user():
    user = make_user(roles=[RoleCode.SECURITY_REVIEWER])
    check = require_roles(RoleCode.SECURITY_REVIEWER, RoleCode.PLATFORM_ADMIN)
    assert check(user) is user


def test_require_roles_dependency_rejects_a_user_without_the_role():
    check = require_roles(RoleCode.PLATFORM_ADMIN)
    with pytest.raises(AppError) as excinfo:
        check(make_user(roles=[RoleCode.DATA_SUBMITTER]))
    assert_app_error(excinfo, 403, ErrorCode.FORBIDDEN)


def test_require_roles_needs_at_least_one_role():
    with pytest.raises(ValueError):
        require_roles()
