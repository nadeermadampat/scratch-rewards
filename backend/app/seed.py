"""Load the demonstration client, campaign and rewards from app_config.yaml.

    python -m app.seed                   # idempotent
    python -m app.seed --demo-activity   # also generate sample participants and cards
"""
from __future__ import annotations

import argparse
import logging
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_app_config, get_settings
from app.core.security import generate_claim_reference, generate_token
from app.models import Campaign, Client, Reward, ScratchCard, SubscriptionVerification, User, utcnow
from app.models.enums import CampaignStatus, CardStatus, RedemptionStatus, VerificationStatus
from app.services import reward_service

logger = logging.getLogger("app.seed")

_SAMPLE_NAMES = [
    "Aarav Menon", "Diya Nair", "Kabir Shah", "Meera Iyer", "Rohan Das", "Ananya Rao",
    "Vikram Pillai", "Sara Thomas", "Imran Khan", "Nisha Varma", "Arjun Reddy", "Leela Joseph",
]


def _with_channel_overrides(platform_config: dict) -> dict:
    """Apply YOUTUBE_CHANNEL_* from the environment on top of a platform_config."""
    settings = get_settings()
    merged = dict(platform_config)
    for key, override in (
        ("channel_id", settings.youtube_channel_id),
        ("channel_url", settings.youtube_channel_url),
        ("channel_name", settings.youtube_channel_name),
    ):
        if override:
            merged[key] = override
    return merged


def seed_demo(db: Session) -> Campaign | None:
    """Create the demo data if it is not there yet. Returns the campaign when created."""
    seed = get_app_config().seed
    if not seed:
        logger.info("No seed section in app config; nothing to do.")
        return None
    client_data, campaign_data = seed["client"], dict(seed["campaign"])
    existing = db.scalar(select(Campaign).where(Campaign.slug == campaign_data["slug"]))
    if existing is not None:
        # Keep the demo campaign's channel in step with `.env` without touching its data.
        synced = _with_channel_overrides(existing.platform_config or {})
        if synced != existing.platform_config:
            existing.platform_config = synced
            db.commit()
            logger.info("Demo campaign already present; channel details updated from .env.")
        else:
            logger.info("Demo campaign already present; nothing to change.")
        return None

    client = db.scalar(select(Client).where(Client.slug == client_data["slug"]))
    if client is None:
        client = Client(**client_data)
        db.add(client)
        db.flush()

    platform_config = _with_channel_overrides(campaign_data.pop("platform_config", {}))

    now = utcnow()
    duration = campaign_data.pop("duration_days", 90)
    campaign = Campaign(
        client_id=client.id,
        platform_config=platform_config,
        starts_at=now - timedelta(days=7),
        ends_at=now + timedelta(days=duration),
        status=CampaignStatus.ACTIVE,
        **campaign_data,
    )
    db.add(campaign)
    db.flush()
    for order, reward in enumerate(seed.get("rewards", [])):
        db.add(Reward(campaign_id=campaign.id, sort_order=order, **reward))
    db.commit()
    logger.info("Seeded campaign '%s' (%s)", campaign.name, campaign.slug)
    return campaign


def seed_demo_activity(db: Session, campaign: Campaign, count: int = 36) -> None:
    """Fabricated participants so the admin dashboard has something to show."""
    rng = random.Random(7)
    now = utcnow()
    for i in range(count):
        generated = now - timedelta(hours=rng.uniform(1, 120))
        name = rng.choice(_SAMPLE_NAMES) if rng.random() < 0.7 else None
        user = User(
            name=name,
            email=f"{name.split()[0].lower()}{i}@example.com" if name and rng.random() < 0.6 else None,
            platform=campaign.platform,
            consent_at=generated,
            created_at=generated,
        )
        db.add(user)
        db.flush()
        verification = SubscriptionVerification(
            campaign_id=campaign.id, user_id=user.id, platform=campaign.platform,
            status=VerificationStatus.VERIFIED, method="simulated", token=generate_token(),
            verified_at=generated, consumed_at=generated, created_at=generated,
        )
        db.add(verification)
        db.flush()
        reward = reward_service.assign_reward(db, campaign.id)
        card = ScratchCard(
            token=generate_token(), user_id=user.id, campaign_id=campaign.id, reward_id=reward.id,
            verification_id=verification.id, generated_at=generated,
            expires_at=generated + timedelta(hours=get_app_config().scratch_card.expiry_hours),
        )
        roll = rng.random()
        if roll < 0.72:
            opened = generated + timedelta(minutes=rng.uniform(0.2, 30))
            card.status = CardStatus.COMPLETED
            card.first_accessed_at = opened
            card.scratch_started_at = opened + timedelta(seconds=rng.uniform(2, 20))
            card.scratch_completed_at = card.scratch_started_at + timedelta(seconds=rng.uniform(3, 12))
            card.claim_reference = generate_claim_reference()
            if reward.is_prize:
                redeemed = rng.random() < 0.3
                card.redemption_status = RedemptionStatus.REDEEMED if redeemed else RedemptionStatus.PENDING
                card.redeemed_at = card.scratch_completed_at + timedelta(hours=2) if redeemed else None
        elif roll < 0.87:
            card.status = CardStatus.OPENED
            card.first_accessed_at = generated + timedelta(minutes=rng.uniform(0.2, 30))
        db.add(card)
    db.commit()
    logger.info("Seeded %d sample participants for '%s'", count, campaign.slug)


def main() -> None:
    from app.core.logging import configure_logging
    from app.db.session import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo-activity", action="store_true", help="also create sample participants")
    args = parser.parse_args()

    configure_logging(get_settings().log_level)
    with SessionLocal() as db:
        campaign = seed_demo(db)
        if campaign is not None and args.demo_activity:
            seed_demo_activity(db, campaign)


if __name__ == "__main__":
    main()
