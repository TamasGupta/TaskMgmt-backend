from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, WorkflowState, WorkflowTransition, TransitionAllowedRole


async def get_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> Workflow | None:
    """Single query: workflow + states (ordered) + transitions + allowed_roles."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))
        .options(
            selectinload(Workflow.states),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.allowed_roles),
        )
    )
    return result.scalar_one_or_none()


async def get_allowed_transitions(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    from_state_key: str,
) -> list[WorkflowTransition]:
    """All permitted next-state transitions from the given state."""
    result = await db.execute(
        select(WorkflowTransition)
        .where(
            WorkflowTransition.workflow_id == workflow_id,
            WorkflowTransition.from_state_key == from_state_key,
        )
        .options(selectinload(WorkflowTransition.allowed_roles))
    )
    return list(result.scalars().all())


async def list_workflows(db: AsyncSession) -> list[Workflow]:
    result = await db.execute(
        select(Workflow)
        .where(Workflow.deleted_at.is_(None))
        .options(
            selectinload(Workflow.states),
            selectinload(Workflow.transitions).selectinload(WorkflowTransition.allowed_roles),
        )
        .order_by(Workflow.name)
    )
    return list(result.scalars().all())
