from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.crud.user import get_users
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserOut],
    summary="List users",
    operation_id="listUsers",
)
async def list_users(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """Return all active users. Results filtered by RLS/RBAC at service level."""
    users = await get_users(db)
    return [UserOut.from_orm_user(u) for u in users]
