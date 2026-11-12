"""Request/response models for the participant-facing API."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class BrandOut(BaseModel):
    primary: str = "#7c3aed"
    accent: str = "#fbbf24"


class ClientOut(BaseModel):
    name: str
    slug: str
    tagline: str | None = None
    logo_url: str | None = None
    brand: BrandOut = BrandOut()


class PlatformOut(BaseModel):
    key: str
    display_name: str
    action_label: str
    brand_color: str
    enabled: bool
    verification_mode: str
    auto_subscribe: bool = False


class EngagementOut(BaseModel):
    url: str
    title: str
    handle: str | None = None
    instructions: list[str] = []


class PrizeTeaserOut(BaseModel):
    name: str
    icon: str | None = None


class ScratchSettingsOut(BaseModel):
    reveal_threshold: float
    expiry_hours: int


class CampaignSummaryOut(BaseModel):
    id: str
    slug: str
    name: str
    headline: str | None = None
    client_name: str
    platform: str


class CampaignOut(BaseModel):
    id: str
    slug: str
    name: str
    headline: str | None = None
    description: str | None = None
    terms: str | None = None
    status: str
    is_open: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    client: ClientOut
    platform: PlatformOut
    engagement: EngagementOut
    prizes: list[PrizeTeaserOut] = []
    scratch: ScratchSettingsOut


class ParticipantRequest(BaseModel):
    """Who is taking part in which campaign, and their consent."""

    model_config = ConfigDict(str_strip_whitespace=True)

    campaign_id: str = Field(min_length=1, max_length=120, description="Campaign id or slug")
    device_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{16,64}$")
    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ()-]{7,20}$")
    consent: bool = False

    @field_validator("name", "phone", "email", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


class AuthorizeResponse(BaseModel):
    #: Where to send the browser (the platform's sign-in / consent page).
    authorization_url: str
    #: Echoed back by the platform; the browser must present it again on return.
    state: str


class OAuthCompleteRequest(BaseModel):
    state: str = Field(min_length=32, max_length=128)
    code: str = Field(min_length=1, max_length=2048)


class VerifyRequest(ParticipantRequest):
    proof: dict[str, Any] = Field(default_factory=dict)

    @field_validator("proof")
    @classmethod
    def _bounded_proof(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value)) > 4000:
            raise ValueError("proof is too large")
        return value


class VerifyResponse(BaseModel):
    verification_id: str
    status: str
    method: str
    message: str | None = None
    #: One-time token to exchange for a scratch card. Present only when verified.
    verification_token: str | None = None
    expires_at: datetime | None = None
    campaign_slug: str | None = None


class IssueCardRequest(BaseModel):
    verification_token: str = Field(min_length=32, max_length=128)


class CardIssuedOut(BaseModel):
    token: str
    url: str
    expires_at: datetime
    #: True when the participant already had a card and it was returned instead of a new one.
    existing: bool = False


class RewardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    reward_type: str
    value: str | None = None
    icon: str | None = None
    is_prize: bool
    redemption_instructions: str | None = None


class CardCampaignOut(BaseModel):
    name: str
    slug: str
    client: ClientOut


class ScratchCardOut(BaseModel):
    reference: str  # short non-secret display id
    status: str
    campaign: CardCampaignOut
    reveal_threshold: float
    generated_at: datetime
    expires_at: datetime
    scratch_started_at: datetime | None = None
    scratch_completed_at: datetime | None = None
    #: Null until scratching has started — never exposed on a card that is merely opened.
    reward: RewardOut | None = None
    #: Null until the card is completed.
    claim_reference: str | None = None
    redemption_status: str
    already_completed: bool = False
