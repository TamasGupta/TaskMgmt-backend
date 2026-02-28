from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import AuthResponse, LoginRequest
from app.services.auth import login_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login user",
    operation_id="loginUser",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate via Supabase Auth and return JWT + user profile."""
    return await login_user(body.email, body.password, db)
