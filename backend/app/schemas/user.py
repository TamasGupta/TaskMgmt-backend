from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    """Verbatim match of OpenAPI User schema – camelCase aliases."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    name: str | None = None
    email: EmailStr
    roleId: uuid.UUID | None = Field(default=None, alias="roleId")
    isActive: bool = Field(default=True, alias="isActive")
    createdAt: datetime = Field(alias="createdAt")

    @classmethod
    def from_orm_user(cls, user: "User") -> "UserOut":  # type: ignore[name-defined]
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            roleId=user.primary_role_id,
            isActive=user.is_active,
            createdAt=user.created_at,
        )
