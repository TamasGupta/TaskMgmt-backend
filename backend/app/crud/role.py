from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role, RolePermission, Permission


async def get_roles_with_permissions(db: AsyncSession) -> list[Role]:
    """Single query: all active roles + nested role_permissions + permissions."""
    result = await db.execute(
        select(Role)
        .where(Role.deleted_at.is_(None))
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
        .order_by(Role.name)
    )
    return list(result.scalars().all())


async def get_role_by_id(db: AsyncSession, role_id: uuid.UUID) -> Role | None:
    result = await db.execute(
        select(Role)
        .where(Role.id == role_id, Role.deleted_at.is_(None))
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )
    return result.scalar_one_or_none()
