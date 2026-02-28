from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.crud.audit import list_audit_logs
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/{eventId}",
    response_model=list[AuditLogOut],
    summary="Get full event audit timeline",
    operation_id="getAuditTimeline",
)
async def get_audit_timeline(
    eventId: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogOut]:
    """Return full audit log for an event, ordered chronologically ASC."""
    event_uuid = uuid.UUID(eventId)
    logs = await list_audit_logs(db, event_uuid)
    return [AuditLogOut.from_orm_log(log) for log in logs]
