"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import client_ip
from app.core.security import constant_time_equals, hash_identifier
from app.services.audit import ClientMeta


def get_client_meta(request: Request) -> ClientMeta:
    return ClientMeta(
        ip_hash=hash_identifier(client_ip(request), get_settings().secret_key),
        user_agent=request.headers.get("user-agent"),
    )


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_key
    if not expected:
        raise AppError(503, "ADMIN_DISABLED", "The admin API is disabled: ADMIN_API_KEY is not set.")
    if not x_admin_key or not constant_time_equals(x_admin_key, expected):
        raise AppError(401, "UNAUTHORIZED", "A valid admin key is required.")
