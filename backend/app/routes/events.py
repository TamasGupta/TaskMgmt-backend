from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.event import EventCreate, EventOut
from app.services.event import create_event_svc, list_events_svc

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    response_model=list[EventOut],
    summary="List events",
    operation_id="listEvents",
)
async def list_events_route(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventOut]:
    """
    Global admins see all events.
    Event-only users see only events they are members of.
    """
    return await list_events_svc(current_user, db)


@router.post(
    "",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create event",
    operation_id="createEvent",
)
async def create_event_route(
    body: EventCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    """Create a new event bound to an existing workflow. Global admin only."""
    return await create_event_svc(body, current_user, db)
