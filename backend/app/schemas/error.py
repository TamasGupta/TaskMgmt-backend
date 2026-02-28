from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard error body matching OpenAPI ErrorResponse schema."""
    model_config = ConfigDict(populate_by_name=True)

    message: str
    code: str = "ERROR"
