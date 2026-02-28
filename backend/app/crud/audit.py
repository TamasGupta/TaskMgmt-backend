from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def create_audit_log(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    event_id: uuid.UUID,
    from_state: str | None,
    to_state: str | None,
    performed_by: uuid.UUID,
    comment: str,
    warning: bool = False,
) -> AuditLog:
    log = AuditLog(
        task_id=task_id,
        event_id=event_id,
        from_state=from_state,
        to_state=to_state,
        performed_by=performed_by,
        comment=comment,
        warning=warning,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def list_audit_logs(db: AsyncSession, event_id: uuid.UUID) -> list[AuditLog]:
    """Ordered ascending by created_at per the mapping.json spec."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.event_id == event_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())
