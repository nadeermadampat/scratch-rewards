"""Campaign lookup, availability rules and public presentation."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_app_config
from app.core.errors import AppError
from app.models import Campaign, utcnow
from app.models.enums import CampaignStatus
from app.providers import get_registry
from app.schemas.public import (
    BrandOut,
    CampaignOut,
    CampaignSummaryOut,
    ClientOut,
    EngagementOut,
    PlatformOut,
    PrizeTeaserOut,
    ScratchSettingsOut,
)


def get_campaign(db: Session, id_or_slug: str) -> Campaign:
    campaign = db.scalar(
        select(Campaign).where(or_(Campaign.id == id_or_slug, Campaign.slug == id_or_slug))
    )
    if campaign is None:
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "This campaign does not exist.")
    return campaign


def is_open(campaign: Campaign) -> bool:
    now = utcnow()
    return (
        campaign.status == CampaignStatus.ACTIVE
        and (campaign.starts_at is None or campaign.starts_at <= now)
        and (campaign.ends_at is None or now <= campaign.ends_at)
    )


def ensure_open(campaign: Campaign) -> None:
    if not is_open(campaign):
        raise AppError(409, "CAMPAIGN_NOT_ACTIVE", "This campaign is not currently running.")


def setting(campaign: Campaign, key: str) -> Any:
    """Campaign-level override, falling back to the `scratch_card` defaults."""
    overrides = campaign.settings or {}
    if overrides.get(key) is not None:
        return overrides[key]
    return getattr(get_app_config().scratch_card, key)


def list_open(db: Session) -> list[CampaignSummaryOut]:
    campaigns = db.scalars(
        select(Campaign).where(Campaign.status == CampaignStatus.ACTIVE).order_by(Campaign.created_at)
    ).all()
    return [
        CampaignSummaryOut(
            id=c.id, slug=c.slug, name=c.name, headline=c.headline,
            client_name=c.client.name, platform=c.platform,
        )
        for c in campaigns
        if is_open(c)
    ]


def client_view(campaign: Campaign) -> ClientOut:
    client = campaign.client
    return ClientOut(
        name=client.name,
        slug=client.slug,
        tagline=client.tagline,
        logo_url=client.logo_url,
        brand=BrandOut(**(client.brand or {})),
    )


def to_public(campaign: Campaign) -> CampaignOut:
    provider = get_registry().get(campaign.platform)
    info = provider.info()
    target = provider.get_engagement_target(campaign.platform_config or {})
    return CampaignOut(
        id=campaign.id,
        slug=campaign.slug,
        name=campaign.name,
        headline=campaign.headline,
        description=campaign.description,
        terms=campaign.terms,
        status=campaign.status,
        is_open=is_open(campaign),
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        client=client_view(campaign),
        platform=PlatformOut(**info.__dict__),
        engagement=EngagementOut(**target.__dict__),
        # Names only: probabilities and stock are never public.
        prizes=[
            PrizeTeaserOut(name=r.name, icon=r.icon)
            for r in campaign.rewards
            if r.is_active and r.is_prize
        ],
        scratch=ScratchSettingsOut(
            reveal_threshold=setting(campaign, "reveal_threshold"),
            expiry_hours=setting(campaign, "expiry_hours"),
        ),
    )
