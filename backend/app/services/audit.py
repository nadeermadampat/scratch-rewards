"""Audit trail: every important business event is persisted and logged."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent

logger = logging.getLogger("app.audit")


@dataclass(frozen=True)
class ClientMeta:
    """Request context worth keeping for fraud analysis. No raw IPs."""

    ip_hash: str | None = None
    user_agent: str | None = None


def record_event(
    db: Session,
    event_type: str,
    *,
    meta: ClientMeta | None = None,
    campaign_id: str | None = None,
    user_id: str | None = None,
    scratch_card_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Add an audit row to the current transaction (the caller commits)."""
    db.add(
        AuditEvent(
            event_type=event_type,
            campaign_id=campaign_id,
            user_id=user_id,
            scratch_card_id=scratch_card_id,
            ip_hash=meta.ip_hash if meta else None,
            user_agent=(meta.user_agent or "")[:300] or None if meta else None,
            payload=payload or {},
        )
    )
    logger.info(
        "event=%s campaign=%s user=%s card=%s %s",
        event_type, campaign_id, user_id, scratch_card_id, payload or "",
    )
