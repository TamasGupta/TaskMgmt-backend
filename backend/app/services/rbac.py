from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import is_global_admin
from app.models.user import User


async def assert_global_admin(user: User) -> None:
    """Raise 403 if the user doesn't have global access_level."""
    if user.access_level != "global":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin access required for this operation.",
        )


async def assert_event_member(
    db: AsyncSession,
    event_id: uuid.UUID,
    user: User,
) -> None:
    """Raise 403 if the user is neither a global admin nor an event member."""
    if user.access_level == "global":
        return
    from app.crud.event import is_event_member  # noqa: PLC0415
    if not await is_event_member(db, event_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this event to perform this action.",
        )


async def assert_can_transition_task(
    user: User,
    db: AsyncSession,
    event_id: uuid.UUID,
) -> None:
    """Either global admin or event member can transition tasks."""
    await assert_event_member(db, event_id, user)
