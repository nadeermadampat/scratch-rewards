"""Subscription verifications and the scratch cards they unlock."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UTCDateTime, new_id, utcnow
from app.models.enums import CardStatus, RedemptionStatus, VerificationStatus
from app.models.reward import Reward
from app.models.tenancy import Campaign
from app.models.user import User


class SubscriptionVerification(Base):
    __tablename__ = "subscription_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default=VerificationStatus.PENDING)
    #: How it was verified: "simulated", "oauth", ...
    method: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text)
    #: One-time hand-off token exchanged for a scratch card. Only set when verified.
    token: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    campaign: Mapped[Campaign] = relationship()
    user: Mapped[User] = relationship()


class ScratchCard(Base):
    __tablename__ = "scratch_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    #: Assigned at generation time and never changed afterwards.
    reward_id: Mapped[str] = mapped_column(ForeignKey("rewards.id"), index=True)
    #: Unique: a verification can unlock at most one card (replay protection).
    verification_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscription_verifications.id"), unique=True
    )
    status: Mapped[str] = mapped_column(String(20), default=CardStatus.ISSUED, index=True)
    claim_reference: Mapped[str | None] = mapped_column(String(24), unique=True, index=True)
    redemption_status: Mapped[str] = mapped_column(
        String(20), default=RedemptionStatus.NOT_APPLICABLE
    )
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    first_accessed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    scratch_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    scratch_completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    redeemed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)

    user: Mapped[User] = relationship()
    campaign: Mapped[Campaign] = relationship()
    reward: Mapped[Reward] = relationship()
