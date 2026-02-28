from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routes import auth, users, events, tasks, audit

logger = logging.getLogger("linkdem")

# ---------------------------------------------------------------------------
# Load exact OpenAPI spec from docs/ for Swagger UI verbatim adherence
# ---------------------------------------------------------------------------
_OPENAPI_PATH = Path(__file__).parent.parent.parent / "docs" / "openapi.json"

def _load_bundled_openapi() -> dict:
    if _OPENAPI_PATH.exists():
        with open(_OPENAPI_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LinkDem API",
    description="Task & Event management system for small teams with RBAC, Workflow Engine, Kanban, and Transition Audit.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Override the OpenAPI schema to match the provided openapi.json exactly
_bundled_spec: dict | None = None


def custom_openapi() -> dict:
    global _bundled_spec
    if _bundled_spec is not None:
        return _bundled_spec

    # Try loading the bundled openapi.json first
    if _OPENAPI_PATH.exists():
        with open(_OPENAPI_PATH, "r", encoding="utf-8") as f:
            _bundled_spec = json.load(f)
        return _bundled_spec

    # Fallback: generate spec from routes using FastAPI's utility (NOT app.openapi()!)
    from fastapi.openapi.utils import get_openapi  # noqa: PLC0415
    _bundled_spec = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    return _bundled_spec


app.openapi = custom_openapi  # type: ignore[method-assign]

# ---------------------------------------------------------------------------
# CORS (open for dev; tighten in prod)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = "; ".join(
        f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": messages, "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    detail = str(exc.orig) if exc.orig else str(exc)
    # Map common constraint names to user-friendly messages
    msg = "A database constraint was violated."
    if "unique" in detail.lower() or "duplicate" in detail.lower():
        msg = "A record with the same unique field already exists."
    elif "foreign key" in detail.lower():
        msg = "Referenced record does not exist."
    elif "not null" in detail.lower():
        msg = "A required field is missing."
    logger.warning("DB IntegrityError: %s", detail)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"message": msg, "code": "CONFLICT"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": str(exc), "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An unexpected error occurred.", "code": "INTERNAL_ERROR"},
    )

# ---------------------------------------------------------------------------
# Routers — all under /api prefix per openapi.json server URL
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "service": "linkdem-backend"}
