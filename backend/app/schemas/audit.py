from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    """Verbatim match of OpenAPI AuditLog schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    taskId: uuid.UUID = Field(alias="taskId")
    eventId: uuid.UUID | None = Field(default=None, alias="eventId")
    fromState: str | None = Field(default=None, alias="fromState")
    toState: str | None = Field(default=None, alias="toState")
    performedBy: uuid.UUID = Field(alias="performedBy")
    comment: str
    warning: bool = False
    timestamp: datetime

    @classmethod
    def from_orm_log(cls, log: "AuditLog") -> "AuditLogOut":  # type: ignore[name-defined]
        return cls(
            id=log.id,
            taskId=log.task_id,
            eventId=log.event_id,
            fromState=log.from_state,
            toState=log.to_state,
            performedBy=log.performed_by,
            comment=log.comment,
            warning=log.warning,
            timestamp=log.created_at,
        )
