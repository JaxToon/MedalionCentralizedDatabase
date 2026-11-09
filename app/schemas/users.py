import uuid

from pydantic import BaseModel, ConfigDict


class _FromOrm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UnitOut(_FromOrm):
    unit_id: uuid.UUID
    unit_code: str
    unit_name: str


class RoleOut(_FromOrm):
    role_code: str
    role_name: str


class UserOut(_FromOrm):
    user_id: uuid.UUID
    username: str
    display_name: str
    email: str
    unit: UnitOut
    roles: list[RoleOut]


class DemoUserList(BaseModel):
    items: list[UserOut]
