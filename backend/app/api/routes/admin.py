"""Admin dashboard API. Every route requires the X-Admin-Key header."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_client_meta, require_admin
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.admin import (
    AdminCampaignOut,
    AdminRewardOut,
    CampaignUpdate,
    OverviewOut,
    RedeemOut,
    RedeemRequest,
    RewardCreate,
    RewardUpdate,
)
from app.schemas.common import ApiResponse, ok
from app.services import admin_service
from app.services.audit import ClientMeta

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(rate_limit("admin")), Depends(require_admin)],
)


@router.get("/overview", response_model=ApiResponse[OverviewOut])
def overview(campaign_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    return ok(admin_service.overview(db, campaign_id))


@router.get("/campaigns", response_model=ApiResponse[list[AdminCampaignOut]])
def list_campaigns(db: Session = Depends(get_db)):
    return ok(admin_service.list_campaigns(db))


@router.patch("/campaigns/{campaign_id}", response_model=ApiResponse[AdminCampaignOut])
def update_campaign(
    campaign_id: str,
    changes: CampaignUpdate,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    return ok(admin_service.update_campaign(db, campaign_id, changes, meta))


@router.get("/campaigns/{campaign_id}/rewards", response_model=ApiResponse[list[AdminRewardOut]])
def list_rewards(campaign_id: str, db: Session = Depends(get_db)):
    return ok([AdminRewardOut.model_validate(r) for r in admin_service.list_rewards(db, campaign_id)])


@router.post(
    "/campaigns/{campaign_id}/rewards", response_model=ApiResponse[AdminRewardOut], status_code=201
)
def create_reward(
    campaign_id: str,
    data: RewardCreate,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    return ok(AdminRewardOut.model_validate(admin_service.create_reward(db, campaign_id, data, meta)))


@router.patch("/rewards/{reward_id}", response_model=ApiResponse[AdminRewardOut])
def update_reward(
    reward_id: str,
    changes: RewardUpdate,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    return ok(AdminRewardOut.model_validate(admin_service.update_reward(db, reward_id, changes, meta)))


@router.post("/redemptions", response_model=ApiResponse[RedeemOut])
def redeem(
    payload: RedeemRequest,
    db: Session = Depends(get_db),
    meta: ClientMeta = Depends(get_client_meta),
):
    """Mark a won reward as redeemed, by its claim reference."""
    return ok(admin_service.redeem(db, payload.claim_reference, meta))
