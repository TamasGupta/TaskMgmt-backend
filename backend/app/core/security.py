from __future__ import annotations

from typing import Any

from app.core.config import settings

# ---------------------------------------------------------------------------
# Supabase JWT Validation
# ---------------------------------------------------------------------------
# Supabase projects issue HS256 JWTs signed with the project JWT secret.
# The most reliable way to validate them without the raw JWT secret is to
# call the Supabase Auth admin API (get_user), which validates server-side.
#
# This avoids needing the raw JWT secret and correctly handles token expiry,
# revocation, and multi-factor refresh scenarios.
# ---------------------------------------------------------------------------


def decode_jwt(token: str) -> dict[str, Any]:
    """
    Validate a Supabase-issued JWT by calling the Auth admin API.
    Returns the payload dict containing 'sub' (auth UID), 'email', etc.
    Raises ValueError on invalid / expired / revoked tokens.

    This approach works for both HS256 and RS256 Supabase projects and
    does not require the raw JWT secret.
    """
    from app.core.supabase import service_client  # noqa: PLC0415  (avoid import cycle)

    try:
        response = service_client.auth.get_user(token)
    except Exception as exc:
        raise ValueError(f"Token validation failed: {exc}") from exc

    if response is None or response.user is None:
        raise ValueError("Token is invalid or has expired.")

    user = response.user
    # Build a payload-like dict from the Supabase user object
    return {
        "sub": str(user.id),
        "email": user.email,
        "role": getattr(user, "role", None),
        "user_metadata": user.user_metadata or {},
    }
