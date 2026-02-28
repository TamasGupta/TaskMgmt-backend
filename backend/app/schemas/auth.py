from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Verbatim match of OpenAPI AuthResponse schema."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    accessToken: str = Field(alias="accessToken")
    refreshToken: str | None = Field(default=None, alias="refreshToken")
    user: UserOut
