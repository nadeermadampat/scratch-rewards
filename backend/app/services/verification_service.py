"""Subscription/follow verification, delegated to the campaign's provider.

Two entry points:
* `verify_subscription` – one request; used when the provider needs no redirect.
* `start_oauth` + `complete_oauth` – the provider sends the participant to its own
  sign-in page and back. The pending verification row carries the `state` value that
  ties the return trip to the browser that started it.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_app_config, get_settings
from app.core.errors import AppError
from app.core.security import generate_token, is_well_formed_token
from app.models import Campaign, SubscriptionVerification, User, utcnow
from app.models.enums import VerificationStatus
from app.providers import get_registry
from app.providers.base import VerificationRequest, VerificationResult
from app.schemas.public import AuthorizeResponse, ParticipantRequest, VerifyRequest, VerifyResponse
from app.services import campaign_service
from app.services.audit import ClientMeta, record_event


def oauth_redirect_uri() -> str:
    """Where the platform sends the browser back to. Must be registered with the platform."""
    return f"{get_settings().app_base_url.rstrip('/')}/oauth/callback"


def _open_campaign(db: Session, payload: ParticipantRequest) -> Campaign:
    campaign = campaign_service.get_campaign(db, payload.campaign_id)
    campaign_service.ensure_open(campaign)
    if not payload.consent:
        raise AppError(422, "CONSENT_REQUIRED", "Please accept the terms and privacy notice to continue.")
    return campaign


def _upsert_user(db: Session, payload: ParticipantRequest, platform: str) -> User:
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


def _apply_result(
    db: Session, verification: SubscriptionVerification, user: User, result: VerificationResult, meta: ClientMeta
) -> VerifyResponse:
    """Record the provider's decision and, when verified, mint the one-time card token."""
    verification.status = result.status
    verification.method = result.method
    verification.detail = result.detail
    verification.token = None
    if result.status == VerificationStatus.VERIFIED:
        now = utcnow()
        verification.token = generate_token()
        verification.verified_at = now
        verification.expires_at = now + timedelta(minutes=get_app_config().verification.token_ttl_minutes)
        if result.platform_user_id:
            # The platform account is the participant's real identity: if it has taken
            # part before (from any browser), this verification belongs to that person.
            owner = db.scalar(
                select(User).where(
                    User.platform == verification.platform,
                    User.platform_user_id == result.platform_user_id,
                    User.id != user.id,
                )
            )
            if owner is not None:
                owner.name = owner.name or user.name
                owner.email = owner.email or user.email
                verification.user_id = owner.id
            else:
                user.platform_user_id = result.platform_user_id
    db.flush()
    record_event(
        db,
        f"verification.{result.status}",
        meta=meta,
        campaign_id=verification.campaign_id,
        user_id=verification.user_id,
        payload={"verification_id": verification.id, "method": result.method},
    )
    db.commit()
    return VerifyResponse(
        verification_id=verification.id,
        status=verification.status,
        method=verification.method,
        message=verification.detail,
        verification_token=verification.token,
        expires_at=verification.expires_at if verification.token else None,
        campaign_slug=verification.campaign.slug,
    )


def verify_subscription(db: Session, payload: VerifyRequest, meta: ClientMeta) -> VerifyResponse:
    campaign = _open_campaign(db, payload)
    provider = get_registry().get_enabled(campaign.platform)
    user = _upsert_user(db, payload, campaign.platform)
    result = provider.verify(
        VerificationRequest(platform_config=campaign.platform_config or {}, proof=payload.proof)
    )
    verification = SubscriptionVerification(
        campaign_id=campaign.id, user_id=user.id, platform=campaign.platform,
        status=VerificationStatus.PENDING, method=result.method,
    )
    db.add(verification)
    return _apply_result(db, verification, user, result, meta)


def start_oauth(db: Session, payload: ParticipantRequest, meta: ClientMeta) -> AuthorizeResponse:
    campaign = _open_campaign(db, payload)
    provider = get_registry().get_enabled(campaign.platform)
    state = generate_token()
    url = provider.start_verification(campaign.platform_config or {}, oauth_redirect_uri(), state)
    if url is None:
        raise AppError(409, "SIGN_IN_NOT_REQUIRED", "This campaign does not use sign-in verification.")

    user = _upsert_user(db, payload, campaign.platform)
    verification = SubscriptionVerification(
        campaign_id=campaign.id,
        user_id=user.id,
        platform=campaign.platform,
        status=VerificationStatus.PENDING,
        method="oauth",
        token=state,  # replaced by the card hand-off token once verified
        expires_at=utcnow() + timedelta(minutes=get_app_config().verification.oauth_state_ttl_minutes),
    )
    db.add(verification)
    db.flush()
    record_event(
        db, "verification.started", meta=meta, campaign_id=campaign.id, user_id=user.id,
        payload={"verification_id": verification.id},
    )
    db.commit()
    return AuthorizeResponse(authorization_url=url, state=state)


def complete_oauth(db: Session, state: str, code: str, meta: ClientMeta) -> VerifyResponse:
    verification = None
    if is_well_formed_token(state):
        verification = db.scalar(
            select(SubscriptionVerification).where(
                SubscriptionVerification.token == state,
                SubscriptionVerification.status == VerificationStatus.PENDING,
            )
        )
    if verification is None:
        # Unknown, already used, or forged state.
        raise AppError(403, "VERIFICATION_INVALID", "This sign-in link is no longer valid. Please start again.")
    if verification.expires_at is not None and verification.expires_at < utcnow():
        raise AppError(410, "VERIFICATION_EXPIRED", "Sign-in took too long. Please start again.")

    campaign = verification.campaign
    campaign_service.ensure_open(campaign)
    provider = get_registry().get_enabled(campaign.platform)

    # Burn the state before calling out, so a replay can never reach the platform twice.
    verification.token = None
    db.commit()

    result = provider.verify(
        VerificationRequest(
            platform_config=campaign.platform_config or {},
            proof={"oauth_code": code, "redirect_uri": oauth_redirect_uri()},
        )
    )
    return _apply_result(db, verification, verification.user, result, meta)
