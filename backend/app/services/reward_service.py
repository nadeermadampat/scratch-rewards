"""Server-side reward allocation. The frontend never takes part in this decision."""
from __future__ import annotations

import random
import secrets
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Reward


class RandomSource(Protocol):
    def random(self) -> float: ...


#: OS-backed CSPRNG, so outcomes cannot be predicted from earlier ones.
_system_rng: RandomSource = secrets.SystemRandom()


def is_eligible(reward: Reward) -> bool:
    in_stock = reward.total_quantity is None or reward.issued_count < reward.total_quantity
    return reward.is_active and reward.weight > 0 and in_stock


def pick_weighted(rewards: Sequence[Reward], rng: RandomSource | None = None) -> Reward:
    """Pick one reward with probability weight / sum(weights)."""
    candidates = [r for r in rewards if r.weight > 0]
    if not candidates:
        raise ValueError("no rewards with a positive weight")
    roll = (rng or _system_rng).random() * sum(r.weight for r in candidates)
    cumulative = 0.0
    for reward in candidates:
        cumulative += reward.weight
        if roll < cumulative:
            return reward
    return candidates[-1]  # guards against floating point drift at the upper edge


def assign_reward(db: Session, campaign_id: str, rng: RandomSource | None = None) -> Reward:
    """Choose a reward for a new card and reserve one unit of its stock.

    Out-of-stock rewards drop out of the draw, so the remaining weights are
    renormalised among what is left. Rows are locked on databases that support it
    so concurrent issuers cannot oversell a capped reward.
    """
    rewards = db.scalars(
        select(Reward)
        .where(Reward.campaign_id == campaign_id, Reward.is_active.is_(True))
        .order_by(Reward.sort_order, Reward.id)
        .with_for_update()
    ).all()
    pool = [r for r in rewards if is_eligible(r)]
    if not pool:
        raise AppError(409, "NO_REWARDS_AVAILABLE", "No rewards are available for this campaign right now.")
    reward = pick_weighted(pool, rng)
    reward.issued_count += 1
    return reward


def seeded_rng(seed: int) -> random.Random:
    """Deterministic source for tests and simulations only."""
    return random.Random(seed)
