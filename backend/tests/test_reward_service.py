from collections import Counter

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.models import Reward
from app.services import reward_service
from app.services.reward_service import assign_reward, pick_weighted, seeded_rng


def _reward(name: str, weight: float, **kwargs) -> Reward:
    return Reward(name=name, weight=weight, is_active=True, is_prize=True, issued_count=0, **kwargs)


def test_distribution_follows_weights():
    rewards = [_reward("a", 10), _reward("b", 30), _reward("c", 60)]
    rng = seeded_rng(42)
    counts = Counter(pick_weighted(rewards, rng).name for _ in range(20_000))
    assert counts["a"] / 20_000 == pytest.approx(0.10, abs=0.015)
    assert counts["b"] / 20_000 == pytest.approx(0.30, abs=0.015)
    assert counts["c"] / 20_000 == pytest.approx(0.60, abs=0.015)


def test_zero_weight_is_never_picked():
    rewards = [_reward("never", 0), _reward("always", 5)]
    rng = seeded_rng(1)
    assert {pick_weighted(rewards, rng).name for _ in range(500)} == {"always"}


def test_pick_requires_a_positive_weight():
    with pytest.raises(ValueError):
        pick_weighted([_reward("none", 0)])


def test_roll_boundaries_map_to_first_and_last():
    rewards = [_reward("first", 1), _reward("last", 1)]

    class Fixed:
        def __init__(self, value):
            self.value = value

        def random(self):
            return self.value

    assert pick_weighted(rewards, Fixed(0.0)).name == "first"
    assert pick_weighted(rewards, Fixed(0.999999)).name == "last"


def test_default_source_is_the_system_csprng():
    import secrets

    assert isinstance(reward_service._system_rng, secrets.SystemRandom)


def test_assign_reserves_stock_and_skips_exhausted_rewards(db, campaign):
    rewards = db.scalars(select(Reward).where(Reward.campaign_id == campaign.id)).all()
    for r in rewards:
        r.is_active = False
    capped = Reward(campaign_id=campaign.id, name="Capped", weight=1000, total_quantity=2, sort_order=90)
    fallback = Reward(campaign_id=campaign.id, name="Fallback", weight=1, is_prize=False, sort_order=91)
    db.add_all([capped, fallback])
    db.commit()

    rng = seeded_rng(3)
    picks = [assign_reward(db, campaign.id, rng).name for _ in range(40)]
    db.commit()

    assert picks.count("Capped") == 2  # never oversold
    assert picks.count("Fallback") == 38
    assert capped.issued_count == 2


def test_assign_fails_cleanly_when_nothing_is_available(db, campaign):
    for r in db.scalars(select(Reward).where(Reward.campaign_id == campaign.id)).all():
        r.is_active = False
    db.commit()
    with pytest.raises(AppError) as error:
        assign_reward(db, campaign.id)
    assert error.value.code == "NO_REWARDS_AVAILABLE"
