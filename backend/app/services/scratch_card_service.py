"""Scratch card lifecycle: issue -> open -> start -> complete (or expire).

Rules enforced here, never in the browser:
* the reward is chosen when the card is issued and is immutable afterwards;
* the reward is disclosed only once scratching has started (an audited transition);
* completion happens exactly once — repeats are answered idempotently;
* expired cards cannot be started or completed.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import generate_claim_reference, generate_token, is_well_formed_token
from app.models import ScratchCard, SubscriptionVerification, utcnow
from app.models.enums import (
    ACTIVE_CARD_STATUSES,
    CardStatus,
    RedemptionStatus,
    VerificationStatus,
)
from app.schemas.public import CardCampaignOut, CardIssuedOut, RewardOut, ScratchCardOut
from app.services import campaign_service, reward_service
from app.services.audit import ClientMeta, record_event

_REWARD_VISIBLE = (CardStatus.SCRATCHING, CardStatus.COMPLETED)


# -- presentation ---------------------------------------------------------

def card_url(token: str) -> str:
    return f"{get_settings().app_base_url.rstrip('/')}/s/{token}"


def to_view(card: ScratchCard, *, already_completed: bool = False) -> ScratchCardOut:
    show_reward = card.status in _REWARD_VISIBLE
    completed = card.status == CardStatus.COMPLETED
    return ScratchCardOut(
        reference=card.id[:8].upper(),
        status=card.status,
        campaign=CardCampaignOut(
            name=card.campaign.name,
            slug=card.campaign.slug,
            client=campaign_service.client_view(card.campaign),
        ),
        reveal_threshold=campaign_service.setting(card.campaign, "reveal_threshold"),
        generated_at=card.generated_at,
        expires_at=card.expires_at,
        scratch_started_at=card.scratch_started_at,
        scratch_completed_at=card.scratch_completed_at,
        reward=RewardOut.model_validate(card.reward) if show_reward else None,
        claim_reference=card.claim_reference if completed else None,
        redemption_status=card.redemption_status,
        already_completed=already_completed,
    )


# -- issuing --------------------------------------------------------------

def issue_card(db: Session, verification_token: str, meta: ClientMeta) -> CardIssuedOut:
    verification = db.scalar(
        select(SubscriptionVerification).where(SubscriptionVerification.token == verification_token)
    )
    if verification is None or verification.status != VerificationStatus.VERIFIED:
        raise AppError(403, "VERIFICATION_INVALID", "Subscription verification is required first.")

    # Replay of an already-used verification: hand back the same card, never a new one.
    existing = db.scalar(select(ScratchCard).where(ScratchCard.verification_id == verification.id))
    if existing is not None:
        return _issued(existing, existing=True)

    if verification.expires_at is not None and verification.expires_at < utcnow():
        raise AppError(410, "VERIFICATION_EXPIRED", "Your verification has expired. Please verify again.")

    campaign = verification.campaign
    campaign_service.ensure_open(campaign)

    # Per-participant cap: return the card they already hold.
    held = db.scalars(
        select(ScratchCard)
        .where(ScratchCard.user_id == verification.user_id, ScratchCard.campaign_id == campaign.id)
        .order_by(ScratchCard.generated_at.desc())
    ).all()
    if len(held) >= campaign_service.setting(campaign, "max_cards_per_user"):
        verification.consumed_at = utcnow()
        record_event(
            db, "card.issue_limit_reached", meta=meta, campaign_id=campaign.id,
            user_id=verification.user_id, scratch_card_id=held[0].id,
        )
        db.commit()
        return _issued(held[0], existing=True)

    now = utcnow()
    reward = reward_service.assign_reward(db, campaign.id)
    card = ScratchCard(
        token=generate_token(),
        user_id=verification.user_id,
        campaign_id=campaign.id,
        reward_id=reward.id,
        verification_id=verification.id,
        status=CardStatus.ISSUED,
        generated_at=now,
        expires_at=now + timedelta(hours=campaign_service.setting(campaign, "expiry_hours")),
    )
    verification.consumed_at = now
    db.add(card)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent request used the same verification first.
        db.rollback()
        winner = db.scalar(select(ScratchCard).where(ScratchCard.verification_id == verification.id))
        if winner is None:
            raise
        return _issued(winner, existing=True)
    record_event(
        db, "card.issued", meta=meta, campaign_id=campaign.id,
        user_id=card.user_id, scratch_card_id=card.id,
    )
    db.commit()
    return _issued(card, existing=False)


def _issued(card: ScratchCard, *, existing: bool) -> CardIssuedOut:
    return CardIssuedOut(
        token=card.token, url=card_url(card.token), expires_at=card.expires_at, existing=existing
    )


# -- lifecycle ------------------------------------------------------------

def _load(db: Session, token: str) -> ScratchCard:
    card = None
    if is_well_formed_token(token):
        card = db.scalar(select(ScratchCard).where(ScratchCard.token == token))
    if card is None:
        raise AppError(404, "CARD_NOT_FOUND", "This scratch card link is not valid.")
    return card


def _expire_if_due(db: Session, card: ScratchCard, meta: ClientMeta) -> bool:
    """Persist expiry the first time an overdue card is touched."""
    if card.status == CardStatus.EXPIRED:
        return True
    if card.status in ACTIVE_CARD_STATUSES and card.expires_at < utcnow():
        card.status = CardStatus.EXPIRED
        record_event(
            db, "card.expired", meta=meta, campaign_id=card.campaign_id,
            user_id=card.user_id, scratch_card_id=card.id,
        )
        db.commit()
        return True
    return False


def _ensure_usable(db: Session, card: ScratchCard, meta: ClientMeta) -> None:
    if _expire_if_due(db, card, meta):
        raise AppError(410, "CARD_EXPIRED", "This scratch card has expired.")


def get_card(db: Session, token: str, meta: ClientMeta) -> ScratchCardOut:
    card = _load(db, token)
    if not _expire_if_due(db, card, meta) and card.status == CardStatus.ISSUED:
        card.status = CardStatus.OPENED
        card.first_accessed_at = utcnow()
        record_event(
            db, "card.opened", meta=meta, campaign_id=card.campaign_id,
            user_id=card.user_id, scratch_card_id=card.id,
        )
        db.commit()
    return to_view(card)


def start_scratch(db: Session, token: str, meta: ClientMeta) -> ScratchCardOut:
    """Record the first scratch. From here on the reward is visible to the card holder."""
    card = _load(db, token)
    if card.status == CardStatus.COMPLETED:
        return to_view(card, already_completed=True)
    _ensure_usable(db, card, meta)
    if card.status != CardStatus.SCRATCHING:
        now = utcnow()
        card.status = CardStatus.SCRATCHING
        card.first_accessed_at = card.first_accessed_at or now
        card.scratch_started_at = now
        record_event(
            db, "card.scratch_started", meta=meta, campaign_id=card.campaign_id,
            user_id=card.user_id, scratch_card_id=card.id,
        )
        db.commit()
    return to_view(card)


def complete_scratch(db: Session, token: str, meta: ClientMeta) -> ScratchCardOut:
    card = _load(db, token)
    if card.status == CardStatus.COMPLETED:
        return _duplicate_completion(db, card, meta)
    _ensure_usable(db, card, meta)

    now = utcnow()
    values = {
        "status": CardStatus.COMPLETED,
        "scratch_completed_at": now,
        "scratch_started_at": card.scratch_started_at or now,
        "first_accessed_at": card.first_accessed_at or now,
        "redemption_status": (
            RedemptionStatus.PENDING if card.reward.is_prize else RedemptionStatus.NOT_APPLICABLE
        ),
    }
    # Compare-and-set: only one request can move the card out of an active state.
    transition = (
        update(ScratchCard)
        .where(ScratchCard.id == card.id, ScratchCard.status.in_(ACTIVE_CARD_STATUSES))
        .execution_options(synchronize_session=False)
    )
    for _ in range(5):
        try:
            changed = db.execute(
                transition.values(**values, claim_reference=generate_claim_reference())
            ).rowcount
            break
        except IntegrityError:  # claim reference collision — draw another
            db.rollback()
    else:
        raise AppError(500, "INTERNAL_ERROR", "Could not complete the card. Please try again.")

    if changed == 0:
        db.rollback()
        db.refresh(card)
        return _duplicate_completion(db, card, meta)

    record_event(
        db, "card.completed", meta=meta, campaign_id=card.campaign_id, user_id=card.user_id,
        scratch_card_id=card.id, payload={"reward_id": card.reward_id},
    )
    db.commit()
    db.refresh(card)
    return to_view(card)


def record_replay(db: Session, token: str, meta: ClientMeta) -> ScratchCardOut:
    """A returning participant scratched their finished card again.

    Purely a tracking event: the reward, claim reference and timestamps are untouched.
    """
    card = _load(db, token)
    if card.status == CardStatus.COMPLETED:
        record_event(
            db, "card.replayed", meta=meta, campaign_id=card.campaign_id,
            user_id=card.user_id, scratch_card_id=card.id,
        )
        db.commit()
    return to_view(card, already_completed=card.status == CardStatus.COMPLETED)


def _duplicate_completion(db: Session, card: ScratchCard, meta: ClientMeta) -> ScratchCardOut:
    record_event(
        db, "card.duplicate_completion", meta=meta, campaign_id=card.campaign_id,
        user_id=card.user_id, scratch_card_id=card.id,
    )
    db.commit()
    return to_view(card, already_completed=True)


def count_cards(db: Session, campaign_id: str | None = None) -> int:
    query = select(func.count(ScratchCard.id))
    if campaign_id:
        query = query.where(ScratchCard.campaign_id == campaign_id)
    return db.scalar(query) or 0
