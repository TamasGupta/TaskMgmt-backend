from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.audit import AuditLogOut
from app.schemas.task import TaskTransitionRequest, TaskOut
from app.services.task import list_tasks_svc, transition_task_svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=list[TaskOut],
    summary="List tasks",
    operation_id="listTasks",
)
async def list_tasks_route(
    eventId: str | None = None,
    assigneeId: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskOut]:
    """
    List tasks. Filtered by eventId and/or assigneeId query params.
    RBAC: global admins see all; event-only users see only tasks in their events.
    """
    event_uuid = uuid.UUID(eventId) if eventId else None
    assignee_uuid = uuid.UUID(assigneeId) if assigneeId else None
    return await list_tasks_svc(db, current_user, event_id=event_uuid, assignee_id=assignee_uuid)


@router.post(
    "/{id}/transition",
    response_model=AuditLogOut,
    summary="Transition task state",
    operation_id="transitionTask",
)
async def transition_task_route(
    id: str,
    body: TaskTransitionRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogOut:
    """
    Perform a workflow state transition on a task.
    Mandatory non-empty comment required.
    Returns the resulting AuditLog entry.
    """
    task_uuid = uuid.UUID(id)
    return await transition_task_svc(task_uuid, body, current_user, db)
