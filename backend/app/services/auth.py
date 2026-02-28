from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.supabase import anon_client
from app.crud.user import upsert_user_profile, get_user_by_auth_uid
from app.schemas.auth import AuthResponse
from app.schemas.user import UserOut


async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
) -> AuthResponse:
    """
    1. Authenticate with Supabase Auth (email + password).
    2. Decode JWT to get auth_uid.
    3. Upsert user profile in users table.
    4. Return AuthResponse with access_token + user.
    """
    try:
        resp = anon_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
        ) from exc

    if not resp.session or not resp.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    session = resp.session
    supabase_user = resp.user

    auth_uid = uuid.UUID(supabase_user.id)
    user_name: str | None = None
    if supabase_user.user_metadata:
        user_name = supabase_user.user_metadata.get("name") or supabase_user.user_metadata.get("full_name")

    # Upsert profile — runs outside transaction; keep simple
    async with db.begin():
        user = await upsert_user_profile(db, auth_uid=auth_uid, email=email, name=user_name)

    # Reload to get role_members
    user = await get_user_by_auth_uid(db, auth_uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    # Elevate access_level for global admins automatically
    from app.crud.user import is_global_admin  # noqa: PLC0415
    if await is_global_admin(db, user.id) and user.access_level != "global":
        from sqlalchemy import update  # noqa: PLC0415
        from app.models.user import User  # noqa: PLC0415
        async with db.begin():
            await db.execute(update(User).where(User.id == user.id).values(access_level="global"))
        user = await get_user_by_auth_uid(db, auth_uid)

    return AuthResponse(
        accessToken=session.access_token,
        refreshToken=session.refresh_token,
        user=UserOut.from_orm_user(user),  # type: ignore[arg-type]
    )
