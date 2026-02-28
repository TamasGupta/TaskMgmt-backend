from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.audit import create_audit_log
from app.crud.event import count_event_tasks, get_event
from app.crud.remark import create_remark
from app.crud.task import (
    acquire_task_lock,
    create_task,
    get_task,
    list_tasks,
    release_task_lock,
    update_task_state,
)
from app.crud.workflow import get_allowed_transitions
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.task import TaskTransitionRequest, TaskOut
from app.services.rbac import assert_can_transition_task

MAX_EVENT_TASKS = 20


async def list_tasks_svc(
    db: AsyncSession,
    current_user: User,
    event_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> list[TaskOut]:
    """
    Global admin sees all tasks matching filters.
    Event-only user sees only tasks from events they belong to (filtered).
    Batched: unique event_ids checked once, not per task row.
    """
    tasks = await list_tasks(db, event_id=event_id, assignee_id=assignee_id)

    if current_user.access_level == "global":
        return [TaskOut.from_orm_task(t) for t in tasks]

    from app.crud.event import is_event_member  # noqa: PLC0415

    # Batch: collect unique event_ids, check membership once per unique event
    event_ids = list({t.event_id for t in tasks})
    memberships: dict[uuid.UUID, bool] = {}
    for eid in event_ids:
        memberships[eid] = await is_event_member(db, eid, current_user.id)

    return [
        TaskOut.from_orm_task(t)
        for t in tasks
        if memberships.get(t.event_id, False)
    ]


async def transition_task_svc(
    task_id: uuid.UUID,
    req: TaskTransitionRequest,
    current_user: User,
    db: AsyncSession,
) -> AuditLogOut:
    """
    Full atomic task state transition:
    1. Fetch task
    2. RBAC: assert user is event member or global admin
    3. Acquire task lock (DB function, outside main txn)
    4. Validate toState is a permitted transition per DAG
    5. Single atomic transaction:
       a. Update task.state_key
       b. Insert remark
       c. Insert audit_log
       d. Auto-create downstream tasks if transition has auto_create_tasks JSON
    6. Release lock (in finally block)
    7. Return AuditLogOut
    """
    to_state = req.toState
    comment = req.comment  # non-empty enforced by Pydantic field_validator

    # --- Step 1: Fetch task ---
    task = await get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    # --- Step 2: RBAC ---
    await assert_can_transition_task(current_user, db, task.event_id)

    # --- Step 3: Acquire lock (optimistic; expires after 5 min) ---
    locked = await acquire_task_lock(db, task_id, current_user.id)
    if not locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is currently locked by another user. Please retry shortly.",
        )

    audit: AuditLogOut | None = None

    try:
        # --- Step 4: Validate transition via workflow DAG ---
        event = await get_event(db, task.event_id)
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

        allowed = await get_allowed_transitions(db, event.workflow_id, task.state_key)
        allowed_keys = {t.to_state_key for t in allowed}
        if to_state not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Transition from '{task.state_key}' to '{to_state}' is not permitted. "
                    f"Allowed next states: {sorted(allowed_keys) or ['none']}."
                ),
            )

        matched_transition = next(
            (t for t in allowed if t.to_state_key == to_state), None
        )

        # --- Step 5: Atomic transaction ---
        old_state = task.state_key

        async with db.begin():
            # 5a. Update task state
            await update_task_state(db, task_id, to_state)

            # 5b. Insert remark
            await create_remark(
                db,
                task_id=task_id,
                event_id=task.event_id,
                user_id=current_user.id,
                remark_text=comment,
            )

            # 5c. Insert audit log (immutable append-only record)
            audit_orm = await create_audit_log(
                db,
                task_id=task_id,
                event_id=task.event_id,
                from_state=old_state,
                to_state=to_state,
                performed_by=current_user.id,
                comment=comment,
                warning=False,
            )

            # 5d. Auto-create downstream tasks if transition defines them
            if matched_transition and matched_transition.auto_create_tasks:
                current_count = await count_event_tasks(db, task.event_id)
                templates: list[dict[str, Any]] = matched_transition.auto_create_tasks  # type: ignore[assignment]

                for tmpl in templates:
                    if current_count >= MAX_EVENT_TASKS:
                        await create_audit_log(
                            db,
                            task_id=task_id,
                            event_id=task.event_id,
                            from_state=None,
                            to_state=None,
                            performed_by=current_user.id,
                            comment=(
                                f"Auto-task creation skipped: event task limit "
                                f"({MAX_EVENT_TASKS}) reached."
                            ),
                            warning=True,
                        )
                        break

                    new_task = await create_task(
                        db,
                        event_id=task.event_id,
                        title=tmpl.get("title", "Auto-generated task"),
                        description=tmpl.get("description"),
                        state_key=tmpl.get("state_key", "todo"),
                        priority=tmpl.get("priority", "medium"),
                        assignee_role_id=(
                            uuid.UUID(tmpl["assignee_role_id"])
                            if tmpl.get("assignee_role_id")
                            else None
                        ),
                    )

                    await create_audit_log(
                        db,
                        task_id=new_task.id,
                        event_id=task.event_id,
                        from_state=None,
                        to_state=new_task.state_key,
                        performed_by=current_user.id,
                        comment=(
                            f"Auto-created by workflow transition "
                            f"'{old_state}' → '{to_state}'."
                        ),
                        warning=False,
                    )
                    current_count += 1

        # Capture the AuditLogOut after transaction committed
        audit = AuditLogOut.from_orm_log(audit_orm)

    finally:
        # --- Step 6: Always release lock ---
        try:
            await release_task_lock(db, task_id, current_user.id)
        except Exception:
            pass

    if audit is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transition failed unexpectedly.",
        )

    return audit
