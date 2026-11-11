"""Read-only catalogue endpoints: campaigns, platforms, rewards."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import Reward
from app.providers import get_registry
from app.schemas.common import ApiResponse, ok
from app.schemas.public import CampaignOut, CampaignSummaryOut, PlatformOut, RewardOut
from app.services import campaign_service

router = APIRouter(dependencies=[Depends(rate_limit("card_read"))])


@router.get("/campaigns", response_model=ApiResponse[list[CampaignSummaryOut]], tags=["campaigns"])
def list_campaigns(db: Session = Depends(get_db)):
    """Campaigns that are currently open."""
    return ok(campaign_service.list_open(db))


@router.get("/campaigns/{campaign_id}", response_model=ApiResponse[CampaignOut], tags=["campaigns"])
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Campaign details by id or slug, including branding and the engagement target."""
    return ok(campaign_service.to_public(campaign_service.get_campaign(db, campaign_id)))


@router.get("/social-platforms", response_model=ApiResponse[list[PlatformOut]], tags=["platforms"])
def list_platforms():
    """All known social platforms and whether each is available."""
    return ok([PlatformOut(**p.info().__dict__) for p in get_registry().all()])


@router.get("/rewards/{reward_id}", response_model=ApiResponse[RewardOut], tags=["rewards"])
def get_reward(reward_id: str, db: Session = Depends(get_db)):
    """Public details of a reward definition (no probabilities, no assignments)."""
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise AppError(404, "REWARD_NOT_FOUND", "This reward does not exist.")
    return ok(RewardOut.model_validate(reward))
