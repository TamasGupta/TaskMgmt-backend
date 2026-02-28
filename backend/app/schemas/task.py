from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskOut(BaseModel):
    """Verbatim match of OpenAPI Task schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    eventId: uuid.UUID = Field(alias="eventId")
    title: str
    description: str | None = None
    assigneeId: uuid.UUID | None = Field(default=None, alias="assigneeId")
    state: str
    priority: Literal["low", "medium", "high"] | None = None
    dueDate: datetime | None = Field(default=None, alias="dueDate")
    createdAt: datetime = Field(alias="createdAt")

    @classmethod
    def from_orm_task(cls, task: "Task") -> "TaskOut":  # type: ignore[name-defined]
        return cls(
            id=task.id,
            eventId=task.event_id,
            title=task.title,
            description=task.description,
            assigneeId=task.assignee_id,
            state=task.state_key,
            priority=task.priority,
            dueDate=task.due_date,
            createdAt=task.created_at,
        )


class TaskTransitionRequest(BaseModel):
    """Request body for POST /tasks/{id}/transition."""
    model_config = ConfigDict(populate_by_name=True)

    toState: str = Field(alias="toState")
    comment: str = Field(alias="comment", description="Mandatory non-empty remark")

    @field_validator("comment")
    @classmethod
    def comment_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("comment must not be empty – every state change requires a remark.")
        return v.strip()

    @field_validator("toState")
    @classmethod
    def to_state_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("toState must not be empty.")
        return v.strip()
