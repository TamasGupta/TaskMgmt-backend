from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import RoleMember


async def get_users(db: AsyncSession) -> list[User]:
    """Fetch all active users with their role_members eagerly loaded. Single query."""
    result = await db.execute(
        select(User)
        .where(User.deleted_at.is_(None))
        .options(selectinload(User.role_members).selectinload(RoleMember.role))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_user_by_auth_uid(db: AsyncSession, auth_uid: uuid.UUID) -> User | None:
    """Lookup user by Supabase auth sub claim."""
    result = await db.execute(
        select(User)
        .where(User.auth_uid == auth_uid, User.deleted_at.is_(None))
        .options(selectinload(User.role_members).selectinload(RoleMember.role))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.role_members).selectinload(RoleMember.role))
    )
    return result.scalar_one_or_none()


async def upsert_user_profile(
    db: AsyncSession,
    auth_uid: uuid.UUID,
    email: str,
    name: str | None = None,
) -> User:
    """
    Insert or update the user profile row on login.
    Uses 'ON CONFLICT' pattern: try to find existing, then insert.
    """
    # Check by auth_uid first
    user = await get_user_by_auth_uid(db, auth_uid)
    if user:
        # Update name if provided
        if name and user.name != name:
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(name=name, updated_at=datetime.utcnow())
            )
            await db.flush()
            user = await get_user_by_auth_uid(db, auth_uid)
        return user  # type: ignore[return-value]

    # Check by email (existing user not yet linked to auth)
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.execute(
            update(User)
            .where(User.id == existing.id)
            .values(auth_uid=auth_uid, updated_at=datetime.utcnow())
        )
        await db.flush()
        return await get_user_by_auth_uid(db, auth_uid)  # type: ignore[return-value]

    # New user
    new_user = User(
        auth_uid=auth_uid,
        email=email,
        name=name,
        is_active=True,
        access_level="event",
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


async def is_global_admin(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Python-level check: does the user have any active global role?"""
    from app.models.role import RoleMember, Role  # noqa: PLC0415

    result = await db.execute(
        select(func.count())
        .select_from(RoleMember)
        .join(Role, Role.id == RoleMember.role_id)
        .where(
            RoleMember.user_id == user_id,
            RoleMember.deleted_at.is_(None),
            Role.is_global.is_(True),
            Role.deleted_at.is_(None),
        )
    )
    return (result.scalar() or 0) > 0
