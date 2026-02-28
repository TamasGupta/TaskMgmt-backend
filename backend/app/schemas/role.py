from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class PermissionOut(BaseModel):
    """Verbatim match of OpenAPI Permission schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    resource: str
    action: Literal["create", "read", "update", "delete"]


class RoleOut(BaseModel):
    """Verbatim match of OpenAPI Role schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    name: str
    permissions: list[PermissionOut] = Field(default_factory=list)

    @classmethod
    def from_orm_role(cls, role: "Role") -> "RoleOut":  # type: ignore[name-defined]
        active_rp = [rp for rp in role.role_permissions if rp.deleted_at is None]
        perms = [
            PermissionOut(resource=rp.permission.resource, action=rp.permission.action)
            for rp in active_rp
        ]
        return cls(id=role.id, name=role.name, permissions=perms)
