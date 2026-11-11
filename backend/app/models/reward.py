"""Reward definitions belonging to a campaign."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UTCDateTime, new_id, utcnow
from app.models.enums import RewardType

if TYPE_CHECKING:
    from app.models.tenancy import Campaign


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    reward_type: Mapped[str] = mapped_column(String(20), default=RewardType.VOUCHER)
    value: Mapped[str | None] = mapped_column(String(60))
    icon: Mapped[str | None] = mapped_column(String(16))
    #: Relative probability weight; chance = weight / sum(weights of eligible rewards).
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    #: False for the "better luck next time" outcome.
    is_prize: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Optional stock cap. NULL means unlimited.
    total_quantity: Mapped[int | None] = mapped_column(Integer)
    issued_count: Mapped[int] = mapped_column(Integer, default=0)
    redemption_instructions: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    campaign: Mapped["Campaign"] = relationship(back_populates="rewards")
