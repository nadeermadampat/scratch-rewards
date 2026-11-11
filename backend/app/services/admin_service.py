"""Read models and configuration changes for the admin dashboard."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import AuditEvent, Campaign, Reward, ScratchCard, User, utcnow
from app.models.enums import CardStatus, RedemptionStatus
from app.schemas.admin import (
    ActivityOut,
    AdminCampaignOut,
    CampaignUpdate,
    OverviewOut,
    RedeemOut,
    RewardCreate,
    RewardDistributionOut,
    RewardUpdate,
    StatsOut,
)
from app.services.audit import ClientMeta, record_event


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def _user_label(user: User) -> str:
    if user.name:
        return user.name
    if user.email:
        return _mask_email(user.email)
    return f"Guest {user.id[:6]}"


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count(model.id)).where(*conditions)) or 0


def overview(db: Session, campaign_id: str | None = None, activity_limit: int = 25) -> OverviewOut:
    card_scope = [ScratchCard.campaign_id == campaign_id] if campaign_id else []
    completed = ScratchCard.status == CardStatus.COMPLETED

    if campaign_id:
        total_users = db.scalar(
            select(func.count(func.distinct(ScratchCard.user_id))).where(*card_scope)
        ) or 0
    else:
        total_users = _count(db, User)

    failed_scope = [AuditEvent.event_type == "verification.failed"]
    if campaign_id:
        failed_scope.append(AuditEvent.campaign_id == campaign_id)

    stats = StatsOut(
        total_users=total_users,
        cards_generated=_count(db, ScratchCard, *card_scope),
        cards_scratched=_count(db, ScratchCard, completed, *card_scope),
        rewards_distributed=db.scalar(
            select(func.count(ScratchCard.id))
            .join(Reward, Reward.id == ScratchCard.reward_id)
            .where(completed, Reward.is_prize.is_(True), *card_scope)
        ) or 0,
        rewards_redeemed=_count(
            db, ScratchCard, ScratchCard.redemption_status == RedemptionStatus.REDEEMED, *card_scope
        ),
        verifications_failed=_count(db, AuditEvent, *failed_scope),
    )

    reward_query = select(Reward).order_by(Reward.campaign_id, Reward.sort_order)
    if campaign_id:
        reward_query = reward_query.where(Reward.campaign_id == campaign_id)
    rewards = db.scalars(reward_query).all()
    counts = {
        (reward_id, status): n
        for reward_id, status, n in db.execute(
            select(ScratchCard.reward_id, ScratchCard.status, func.count(ScratchCard.id))
            .where(*card_scope)
            .group_by(ScratchCard.reward_id, ScratchCard.status)
        )
    }
    weight_by_campaign: dict[str, float] = {}
    for r in rewards:
        if r.is_active:
            weight_by_campaign[r.campaign_id] = weight_by_campaign.get(r.campaign_id, 0) + r.weight
    distribution = [
        RewardDistributionOut(
            reward_id=r.id,
            name=r.name,
            icon=r.icon,
            is_prize=r.is_prize,
            is_active=r.is_active,
            weight=r.weight,
            configured_share=(
                r.weight / weight_by_campaign[r.campaign_id]
                if r.is_active and weight_by_campaign.get(r.campaign_id)
                else 0.0
            ),
            total_quantity=r.total_quantity,
            assigned=sum(n for (rid, _), n in counts.items() if rid == r.id),
            revealed=counts.get((r.id, CardStatus.COMPLETED), 0),
        )
        for r in rewards
    ]

    cards = db.scalars(
        select(ScratchCard).where(*card_scope).order_by(ScratchCard.generated_at.desc()).limit(activity_limit)
    ).all()
    activity = [
        ActivityOut(
            card_reference=c.id[:8].upper(),
            user_label=_user_label(c.user),
            campaign_name=c.campaign.name,
            status=c.status,
            reward_name=c.reward.name if c.status == CardStatus.COMPLETED else None,
            claim_reference=c.claim_reference,
            redemption_status=c.redemption_status,
            generated_at=c.generated_at,
            completed_at=c.scratch_completed_at,
        )
        for c in cards
    ]
    return OverviewOut(stats=stats, distribution=distribution, recent_activity=activity)


def list_campaigns(db: Session) -> list[AdminCampaignOut]:
    return [_campaign_view(c) for c in db.scalars(select(Campaign).order_by(Campaign.created_at)).all()]


def _campaign_view(c: Campaign) -> AdminCampaignOut:
    return AdminCampaignOut(
        id=c.id, slug=c.slug, name=c.name, client_name=c.client.name, platform=c.platform,
        status=c.status, starts_at=c.starts_at, ends_at=c.ends_at,
    )


def update_campaign(db: Session, campaign_id: str, changes: CampaignUpdate, meta: ClientMeta) -> AdminCampaignOut:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "This campaign does not exist.")
    data = changes.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in data.items():
        setattr(campaign, field, value)
    record_event(db, "admin.campaign_updated", meta=meta, campaign_id=campaign.id, payload=data)
    db.commit()
    return _campaign_view(campaign)


def list_rewards(db: Session, campaign_id: str) -> list[Reward]:
    return list(
        db.scalars(select(Reward).where(Reward.campaign_id == campaign_id).order_by(Reward.sort_order)).all()
    )


def create_reward(db: Session, campaign_id: str, data: RewardCreate, meta: ClientMeta) -> Reward:
    if db.get(Campaign, campaign_id) is None:
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "This campaign does not exist.")
    next_order = (db.scalar(select(func.max(Reward.sort_order)).where(Reward.campaign_id == campaign_id)) or 0) + 1
    reward = Reward(campaign_id=campaign_id, sort_order=next_order, **data.model_dump())
    db.add(reward)
    db.flush()
    record_event(db, "admin.reward_created", meta=meta, campaign_id=campaign_id, payload={"reward_id": reward.id})
    db.commit()
    return reward


def update_reward(db: Session, reward_id: str, changes: RewardUpdate, meta: ClientMeta) -> Reward:
    """Affects future cards only: rewards already assigned to cards never change."""
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise AppError(404, "REWARD_NOT_FOUND", "This reward does not exist.")
    data = changes.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is None and field != "total_quantity":
            continue
        setattr(reward, field, value)
    record_event(
        db, "admin.reward_updated", meta=meta, campaign_id=reward.campaign_id,
        payload={"reward_id": reward.id, **data},
    )
    db.commit()
    return reward


def redeem(db: Session, claim_reference: str, meta: ClientMeta) -> RedeemOut:
    card = db.scalar(
        select(ScratchCard).where(ScratchCard.claim_reference == claim_reference.strip().upper())
    )
    if card is None or card.status != CardStatus.COMPLETED:
        raise AppError(404, "CLAIM_NOT_FOUND", "No completed card matches this claim reference.")
    if card.redemption_status == RedemptionStatus.NOT_APPLICABLE:
        raise AppError(409, "NOTHING_TO_REDEEM", "This card did not win a prize.")
    if card.redemption_status == RedemptionStatus.REDEEMED:
        raise AppError(409, "ALREADY_REDEEMED", "This reward has already been redeemed.")
    card.redemption_status = RedemptionStatus.REDEEMED
    card.redeemed_at = utcnow()
    record_event(
        db, "reward.redeemed", meta=meta, campaign_id=card.campaign_id,
        user_id=card.user_id, scratch_card_id=card.id,
    )
    db.commit()
    return RedeemOut(
        claim_reference=card.claim_reference or "",
        reward_name=card.reward.name,
        redemption_status=card.redemption_status,
        redeemed_at=card.redeemed_at,
    )
