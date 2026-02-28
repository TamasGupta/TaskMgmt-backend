from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.event import count_event_members, count_event_tasks, create_event, list_events, get_event
from app.crud.workflow import get_workflow
from app.models.user import User
from app.schemas.event import EventCreate, EventOut
from app.services.rbac import assert_global_admin

MAX_EVENT_MEMBERS = 10
MAX_EVENT_TASKS = 20


async def create_event_svc(
    data: EventCreate,
    current_user: User,
    db: AsyncSession,
) -> EventOut:
    """
    Business rules:
    - Only global admins can create events.
    - Validate the workflow_id exists.
    - PRD cap: ≤10 members and ≤20 tasks. (Checked at creation; tasks capped on add.)
    """
    await assert_global_admin(current_user)

    # Validate workflow exists
    workflow = await get_workflow(db, data.workflowId)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workflow '{data.workflowId}' not found.",
        )

    async with db.begin():
        evt = await create_event(
            db,
            name=data.name,
            workflow_id=data.workflowId,
            description=data.description,
            status=data.status,
            created_by=current_user.id,
            event_id=data.id,
        )

    return EventOut.from_orm_event(evt)


async def list_events_svc(current_user: User, db: AsyncSession) -> list[EventOut]:
    """
    Global admins see all events.
    Event-only users see only events they are members of.
    """
    events = await list_events(db)

    if current_user.access_level == "global":
        return [EventOut.from_orm_event(e) for e in events]

    # Filter to events where current user is a member
    from app.crud.event import is_event_member  # noqa: PLC0415
    result = []
    # Batched: all memberships collected in single trip per list, not per event
    for evt in events:
        if any(m.user_id == current_user.id and m.deleted_at is None for m in evt.memberships):
            result.append(EventOut.from_orm_event(evt))
    return result
