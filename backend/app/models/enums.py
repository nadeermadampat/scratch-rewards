"""Status vocabularies. Stored as plain strings so they stay portable across databases."""
from __future__ import annotations

from enum import StrEnum


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class CardStatus(StrEnum):
    ISSUED = "issued"          # generated, never opened
    OPENED = "opened"          # card page viewed
    SCRATCHING = "scratching"  # first scratch recorded; reward disclosed to the client
    COMPLETED = "completed"    # reveal threshold reached and saved
    EXPIRED = "expired"


#: States from which a card can still be scratched/completed.
ACTIVE_CARD_STATUSES = (CardStatus.ISSUED, CardStatus.OPENED, CardStatus.SCRATCHING)


class RedemptionStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"  # no-prize outcome, or card not completed yet
    PENDING = "pending"
    REDEEMED = "redeemed"


class RewardType(StrEnum):
    VOUCHER = "voucher"
    PRODUCT = "product"
    DISCOUNT = "discount"
    SURPRISE = "surprise"
    NONE = "none"
