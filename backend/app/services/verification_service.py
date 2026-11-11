"""Subscription/follow verification, delegated to the campaign's provider."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_app_config
from app.core.errors import AppError
from app.core.security import generate_token
from app.models import SubscriptionVerification, User, utcnow
from app.models.enums import VerificationStatus
from app.providers import get_registry
from app.providers.base import VerificationRequest
from app.schemas.public import VerifyRequest, VerifyResponse
from app.services import campaign_service
from app.services.audit import ClientMeta, record_event


def _upsert_user(db: Session, payload: VerifyRequest, platform: str) -> User:
    user = None
    if payload.device_id:
        user = db.scalar(select(User).where(User.anonymous_id == payload.device_id))
    if user is None:
        user = User(anonymous_id=payload.device_id, platform=platform)
        db.add(user)
    # Only overwrite contact details the participant actually supplied.
    user.name = payload.name or user.name
    user.email = (str(payload.email).lower() if payload.email else None) or user.email
    user.phone = payload.phone or user.phone
    user.consent_at = user.consent_at or utcnow()
    db.flush()
    return user


def verify_subscription(db: Session, payload: VerifyRequest, meta: ClientMeta) -> VerifyResponse:
    campaign = campaign_service.get_campaign(db, payload.campaign_id)
    campaign_service.ensure_open(campaign)
    if not payload.consent:
        raise AppError(422, "CONSENT_REQUIRED", "Please accept the terms and privacy notice to continue.")

    provider = get_registry().get_enabled(campaign.platform)
    user = _upsert_user(db, payload, campaign.platform)
    result = provider.verify(
        VerificationRequest(platform_config=campaign.platform_config or {}, proof=payload.proof)
    )

    verification = SubscriptionVerification(
        campaign_id=campaign.id,
        user_id=user.id,
        platform=campaign.platform,
        status=result.status,
        method=result.method,
        detail=result.detail,
    )
    if result.status == VerificationStatus.VERIFIED:
        now = utcnow()
        verification.token = generate_token()
        verification.verified_at = now
        verification.expires_at = now + timedelta(
            minutes=get_app_config().verification.token_ttl_minutes
        )
        if result.platform_user_id:
            user.platform_user_id = result.platform_user_id
    db.add(verification)
    db.flush()
    record_event(
        db,
        f"verification.{result.status}",
        meta=meta,
        campaign_id=campaign.id,
        user_id=user.id,
        payload={"verification_id": verification.id, "method": result.method},
    )
    db.commit()

    return VerifyResponse(
        verification_id=verification.id,
        status=verification.status,
        method=verification.method,
        message=verification.detail,
        verification_token=verification.token,
        expires_at=verification.expires_at,
    )
