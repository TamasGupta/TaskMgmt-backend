from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStateOut(BaseModel):
    """Verbatim match of OpenAPI WorkflowState schema.
    id = workflow_states.key (string key, not UUID) per mapping.json."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str  # maps to workflow_states.key
    name: str
    type: Literal["todo", "in_progress", "done"] | None = None


class WorkflowTransitionOut(BaseModel):
    """Verbatim match of OpenAPI WorkflowTransition schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    from_: str = Field(alias="from")
    to: str
    allowedRoles: list[str] = Field(default_factory=list, alias="allowedRoles")
    autoCreateTasks: list[str] = Field(default_factory=list, alias="autoCreateTasks")


class WorkflowOut(BaseModel):
    """Verbatim match of OpenAPI Workflow schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    name: str
    states: list[WorkflowStateOut] = Field(default_factory=list)
    transitions: list[WorkflowTransitionOut] = Field(default_factory=list)
