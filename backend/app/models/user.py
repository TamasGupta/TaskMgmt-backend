from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_uid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, index=True, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    access_level: Mapped[str] = mapped_column(String(20), nullable=False, default="event")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Use string reference to avoid circular imports
    role_members: Mapped[list["RoleMember"]] = relationship(  # type: ignore[name-defined]
        "RoleMember",
        back_populates="user",
        lazy="selectin",
        foreign_keys="[RoleMember.user_id]",
    )

    @property
    def primary_role_id(self) -> uuid.UUID | None:
        """Return the first active role membership's role_id."""
        active = [rm for rm in self.role_members if rm.deleted_at is None]
        return active[0].role_id if active else None
