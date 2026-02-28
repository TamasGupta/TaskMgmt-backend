from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.models.user import User


async def list_tasks(
    db: AsyncSession,
    event_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> list[Task]:
    """Bounded query: tasks with assignee eagerly loaded. No per-row fetches."""
    stmt = (
        select(Task)
        .where(Task.deleted_at.is_(None))
        .options(selectinload(Task.assignee))
        .order_by(Task.created_at)
    )
    if event_id:
        stmt = stmt.where(Task.event_id == event_id)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id, Task.deleted_at.is_(None))
        .options(selectinload(Task.assignee))
    )
    return result.scalar_one_or_none()


async def update_task_state(
    db: AsyncSession,
    task_id: uuid.UUID,
    new_state_key: str,
) -> None:
    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(state_key=new_state_key, updated_at=datetime.utcnow())
    )


async def create_task(
    db: AsyncSession,
    *,
    event_id: uuid.UUID,
    title: str,
    state_key: str,
    description: str | None = None,
    assignee_id: uuid.UUID | None = None,
    assignee_role_id: uuid.UUID | None = None,
    priority: str = "medium",
    due_date: datetime | None = None,
) -> Task:
    task = Task(
        event_id=event_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        assignee_role_id=assignee_role_id,
        state_key=state_key,
        priority=priority,
        due_date=due_date,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def acquire_task_lock(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Calls the DB app_acquire_task_lock() function atomically."""
    result = await db.execute(
        text("SELECT app_acquire_task_lock(:task_id, :user_id)"),
        {"task_id": str(task_id), "user_id": str(user_id)},
    )
    return bool(result.scalar())


async def release_task_lock(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Calls the DB app_release_task_lock() function."""
    result = await db.execute(
        text("SELECT app_release_task_lock(:task_id, :user_id)"),
        {"task_id": str(task_id), "user_id": str(user_id)},
    )
    return bool(result.scalar())
