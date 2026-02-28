from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, EventMembership
from app.models.workflow import Workflow


async def list_events(db: AsyncSession) -> list[Event]:
    """Single batched query: all non-deleted events with workflow eagerly loaded."""
    result = await db.execute(
        select(Event)
        .where(Event.deleted_at.is_(None))
        .options(selectinload(Event.workflow))
        .order_by(Event.created_at.desc())
    )
    return list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: uuid.UUID) -> Event | None:
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id, Event.deleted_at.is_(None))
        .options(selectinload(Event.workflow))
    )
    return result.scalar_one_or_none()


async def create_event(
    db: AsyncSession,
    *,
    name: str,
    workflow_id: uuid.UUID,
    description: str | None = None,
    status: str | None = None,
    created_by: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> Event:
    evt = Event(
        id=event_id or uuid.uuid4(),
        name=name,
        description=description,
        workflow_id=workflow_id,
        status=status,
        created_by=created_by,
    )
    db.add(evt)
    await db.flush()
    await db.refresh(evt)
    return evt


async def count_event_members(db: AsyncSession, event_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(EventMembership)
        .where(
            EventMembership.event_id == event_id,
            EventMembership.deleted_at.is_(None),
        )
    )
    return result.scalar() or 0


async def count_event_tasks(db: AsyncSession, event_id: uuid.UUID) -> int:
    from app.models.task import Task  # noqa: PLC0415

    result = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.event_id == event_id, Task.deleted_at.is_(None))
    )
    return result.scalar() or 0


async def is_event_member(db: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(func.count())
        .select_from(EventMembership)
        .where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user_id,
            EventMembership.deleted_at.is_(None),
        )
    )
    return (result.scalar() or 0) > 0
