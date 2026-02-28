from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remark import Remark


async def create_remark(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    remark_text: str,
) -> Remark:
    remark = Remark(
        task_id=task_id,
        event_id=event_id,
        user_id=user_id,
        remark=remark_text,
    )
    db.add(remark)
    await db.flush()
    return remark
