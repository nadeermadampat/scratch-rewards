"""Clients (businesses) and their campaigns."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UTCDateTime, new_id, utcnow
from app.models.enums import CampaignStatus

if TYPE_CHECKING:
    from app.models.reward import Reward


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    tagline: Mapped[str | None] = mapped_column(String(240))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    brand: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="client")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    headline: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    terms: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    #: Provider-specific target, e.g. {"channel_id", "channel_url", "channel_name"} for YouTube.
    platform_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    #: Optional overrides of `scratch_card.*` defaults from app_config.yaml.
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(20), default=CampaignStatus.DRAFT, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    client: Mapped[Client] = relationship(back_populates="campaigns")
    rewards: Mapped[list["Reward"]] = relationship(
        back_populates="campaign", order_by="Reward.sort_order"
    )
