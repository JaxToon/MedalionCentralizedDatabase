from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDep
from app.db.repositories import users
from app.schemas.errors import ErrorResponse
from app.schemas.users import DemoUserList, UserOut

router = APIRouter(tags=["users"])


@router.get("/demo-users")
def list_demo_users(session: SessionDep) -> DemoUserList:
    """Active demo users, for the UI's user switcher. Needs no demo user header."""
    return DemoUserList(
        items=[UserOut.model_validate(user) for user in users.list_active_users(session)]
    )


@router.get("/me", responses={401: {"model": ErrorResponse}})
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
