"""In-memory sliding-window rate limiter.

Good for a single process. Swap `SlidingWindowLimiter` for a Redis-backed
implementation with the same `check` signature when running multiple workers.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from fastapi import Request

from app.core.config import get_app_config, get_settings
from app.core.errors import AppError


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False, max(1, int(window_seconds - (now - hits[0])) + 1)
            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    if get_settings().trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str) -> Callable[[Request], None]:
    """FastAPI dependency enforcing the `rate_limits.<bucket>` rule per client IP."""

    def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        rule = get_app_config().rate_limits.get(bucket)
        if rule is None:
            return
        allowed, retry_after = limiter.check(
            f"{bucket}:{client_ip(request)}", rule.limit, rule.window_seconds
        )
        if not allowed:
            raise AppError(
                429,
                "RATE_LIMITED",
                "Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
