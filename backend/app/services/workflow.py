from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.workflow import get_workflow, list_workflows
from app.models.user import User
from app.schemas.workflow import WorkflowOut, WorkflowStateOut, WorkflowTransitionOut


def _build_workflow_out(wf) -> WorkflowOut:
    states = [
        WorkflowStateOut(id=s.key, name=s.name, type=s.type)  # type: ignore[call-arg]
        for s in wf.states
    ]
    transitions = []
    for t in wf.transitions:
        auto_tasks = []
        if t.auto_create_tasks:
            auto_tasks = [
                tmpl.get("title", "Auto-task")
                for tmpl in t.auto_create_tasks
                if isinstance(tmpl, dict)
            ]
        transitions.append(
            WorkflowTransitionOut(
                **{
                    "from": t.from_state_key,
                    "to": t.to_state_key,
                    "allowedRoles": [str(ar.role_id) for ar in t.allowed_roles],
                    "autoCreateTasks": auto_tasks,
                }
            )
        )
    return WorkflowOut(id=wf.id, name=wf.name, states=states, transitions=transitions)


async def get_workflow_svc(workflow_id: uuid.UUID, db: AsyncSession) -> WorkflowOut | None:
    wf = await get_workflow(db, workflow_id)
    if wf is None:
        return None
    return _build_workflow_out(wf)


async def list_workflows_svc(db: AsyncSession) -> list[WorkflowOut]:
    workflows = await list_workflows(db)
    return [_build_workflow_out(wf) for wf in workflows]
