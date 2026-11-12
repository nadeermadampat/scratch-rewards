"""Models for the admin dashboard API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StatsOut(BaseModel):
    total_users: int
    cards_generated: int
    cards_scratched: int
    rewards_distributed: int
    rewards_redeemed: int
    verifications_failed: int


class RewardDistributionOut(BaseModel):
    reward_id: str
    name: str
    icon: str | None = None
    is_prize: bool
    is_active: bool
    weight: float
    configured_share: float  # weight / total active weight, 0..1
    total_quantity: int | None = None
    assigned: int
    revealed: int


class ActivityOut(BaseModel):
    card_reference: str
    user_label: str
    campaign_name: str
    status: str
    reward_name: str | None = None  # only for completed cards
    claim_reference: str | None = None
    redemption_status: str
    generated_at: datetime
    completed_at: datetime | None = None
    #: Times the participant came back through the campaign and was given this card again.
    return_visits: int = 0
    #: Times the finished card was scratched again.
    replays: int = 0


class OverviewOut(BaseModel):
    stats: StatsOut
    distribution: list[RewardDistributionOut]
    recent_activity: list[ActivityOut]


class AdminCampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    client_name: str
    platform: str
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_cards_per_user: int = 1


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    status: Literal["draft", "active", "paused", "ended"] | None = None
    #: How many cards one participant may receive in this campaign.
    max_cards_per_user: int | None = Field(default=None, ge=1, le=1000)


class AdminRewardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    name: str
    description: str | None = None
    reward_type: str
    value: str | None = None
    icon: str | None = None
    weight: float
    is_prize: bool
    total_quantity: int | None = None
    issued_count: int
    redemption_instructions: str | None = None
    is_active: bool


class RewardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    reward_type: Literal["voucher", "product", "discount", "surprise", "none"] = "voucher"
    value: str | None = Field(default=None, max_length=60)
    icon: str | None = Field(default=None, max_length=16)
    weight: float = Field(default=1, ge=0, le=1_000_000)
    is_prize: bool = True
    total_quantity: int | None = Field(default=None, ge=0)
    redemption_instructions: str | None = Field(default=None, max_length=500)


class RewardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    weight: float | None = Field(default=None, ge=0, le=1_000_000)
    total_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class RedeemRequest(BaseModel):
    claim_reference: str = Field(min_length=6, max_length=24)


class RedeemOut(BaseModel):
    claim_reference: str
    reward_name: str
    redemption_status: str
    redeemed_at: datetime | None = None
