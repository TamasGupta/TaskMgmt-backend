from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    """Request body for POST /events."""
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID | None = None
    name: str
    description: str | None = None
    workflowId: uuid.UUID = Field(alias="workflowId")
    status: str | None = None
    createdBy: uuid.UUID | None = Field(default=None, alias="createdBy")


class EventOut(BaseModel):
    """Verbatim match of OpenAPI Event schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    workflowId: uuid.UUID = Field(alias="workflowId")
    status: str | None = None
    createdBy: uuid.UUID | None = Field(default=None, alias="createdBy")
    createdAt: datetime = Field(alias="createdAt")

    @classmethod
    def from_orm_event(cls, event: "Event") -> "EventOut":  # type: ignore[name-defined]
        return cls(
            id=event.id,
            name=event.name,
            description=event.description,
            workflowId=event.workflow_id,
            status=event.status,
            createdBy=event.created_by,
            createdAt=event.created_at,
        )
