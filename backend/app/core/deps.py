from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_jwt

_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Validate the Bearer JWT and return the corresponding User ORM object.
    Imported models lazily to avoid circular imports.
    """
    from app.crud.user import get_user_by_auth_uid  # noqa: PLC0415

    try:
        payload = decode_jwt(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    auth_uid_str: str | None = payload.get("sub")
    if not auth_uid_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_uid = UUID(auth_uid_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sub claim format",
        ) from exc

    user = await get_user_by_auth_uid(db, auth_uid)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found. Please log in via /auth/login first.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def require_global_admin(
    current_user=Depends(get_current_user),
):
    """Dependency: raises 403 unless user has 'global' access_level."""
    if current_user.access_level != "global":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin access required.",
        )
    return current_user


async def require_event_member(
    event_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dependency: raises 403 unless user is a member of the given event (or global admin)."""
    from app.crud.event import is_event_member  # noqa: PLC0415

    if current_user.access_level == "global":
        return current_user

    member = await is_event_member(db, event_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this event.",
        )
    return current_user
