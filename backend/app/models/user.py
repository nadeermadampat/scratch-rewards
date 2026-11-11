"""Participants. Personal fields are optional by design (data minimisation)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UTCDateTime, new_id, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    #: Random per-browser identifier; lets a returning visitor get their existing card back.
    anonymous_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    platform: Mapped[str | None] = mapped_column(String(40))
    #: Channel/profile id on the social platform, when the provider can supply one.
    platform_user_id: Mapped[str | None] = mapped_column(String(160), index=True)
    consent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
