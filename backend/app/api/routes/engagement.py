"""The participant journey: verify -> issue card -> open -> start -> complete."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.common import ApiResponse, ok
from app.schemas.public import (
    AuthorizeResponse,
    CardIssuedOut,
    IssueCardRequest,
    OAuthCompleteRequest,
    ParticipantRequest,
    ScratchCardOut,
    VerifyRequest,
    VerifyResponse,
)
from app.services import scratch_card_service, verification_service
from app.services.audit import ClientMeta

router = APIRouter()


@router.post(
    "/subscriptions/verify",
    response_model=ApiResponse[VerifyResponse],
    dependencies=[Depends(rate_limit("verify"))],
    tags=["subscriptions"],
)
def verify_subscription(
    payload: VerifyRequest,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    """Verify (or, in the MVP, simulate) the subscription for a campaign."""
    return ok(verification_service.verify_subscription(db, payload, meta))


@router.post(
    "/subscriptions/authorize",
    response_model=ApiResponse[AuthorizeResponse],
    dependencies=[Depends(rate_limit("verify"))],
    tags=["subscriptions"],
)
def authorize_subscription(
    payload: ParticipantRequest,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    """Start sign-in verification: returns the platform URL to send the browser to."""
    return ok(verification_service.start_oauth(db, payload, meta))


@router.post(
    "/subscriptions/oauth/complete",
    response_model=ApiResponse[VerifyResponse],
    dependencies=[Depends(rate_limit("verify"))],
    tags=["subscriptions"],
)
def complete_oauth(
    payload: OAuthCompleteRequest,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    """Finish sign-in verification with the `state` and `code` the platform returned."""
    return ok(verification_service.complete_oauth(db, payload.state, payload.code, meta))


@router.post(
    "/scratch-cards",
    response_model=ApiResponse[CardIssuedOut],
    status_code=201,
    dependencies=[Depends(rate_limit("issue_card"))],
    tags=["scratch-cards"],
)
def issue_scratch_card(
    payload: IssueCardRequest,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    """Exchange a verification token for a scratch card. The reward is assigned here."""
    return ok(scratch_card_service.issue_card(db, payload.verification_token, meta))


@router.get(
    "/scratch-cards/{token}",
    response_model=ApiResponse[ScratchCardOut],
    dependencies=[Depends(rate_limit("card_read"))],
    tags=["scratch-cards"],
)
def get_scratch_card(
    token: str, db: Session = Depends(get_db), meta: ClientMeta = Depends(get_client_meta)
):
    """Card state. The reward is omitted until scratching has started."""
    return ok(scratch_card_service.get_card(db, token, meta))


@router.post(
    "/scratch-cards/{token}/start",
    response_model=ApiResponse[ScratchCardOut],
    dependencies=[Depends(rate_limit("card_write"))],
    tags=["scratch-cards"],
)
def start_scratch(
    token: str, db: Session = Depends(get_db), meta: ClientMeta = Depends(get_client_meta)
):
    """Record the first scratch and disclose the pre-assigned reward to the card holder."""
    return ok(scratch_card_service.start_scratch(db, token, meta))


@router.post(
    "/scratch-cards/{token}/replay",
    response_model=ApiResponse[ScratchCardOut],
    dependencies=[Depends(rate_limit("card_write"))],
    tags=["scratch-cards"],
)
def replay_scratch(
    token: str, db: Session = Depends(get_db), meta: ClientMeta = Depends(get_client_meta)
):
    """Record that a finished card was scratched again. The result never changes."""
    return ok(scratch_card_service.record_replay(db, token, meta))


@router.post(
    "/scratch-cards/{token}/complete",
    response_model=ApiResponse[ScratchCardOut],
    dependencies=[Depends(rate_limit("card_write"))],
    tags=["scratch-cards"],
)
def complete_scratch(
    token: str, db: Session = Depends(get_db), meta: ClientMeta = Depends(get_client_meta)
):
    """Complete the card once. Repeats return the same result with already_completed=true."""
    return ok(scratch_card_service.complete_scratch(db, token, meta))
