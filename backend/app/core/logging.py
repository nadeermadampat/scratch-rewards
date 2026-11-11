"""Logging setup and per-request access logging."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

access_logger = logging.getLogger("app.access")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )


def _redact(path: str) -> str:
    """Scratch card tokens are bearer secrets; keep them out of the logs."""
    marker = "/scratch-cards/"
    if marker in path:
        head, _, tail = path.partition(marker)
        token, sep, rest = tail.partition("/")
        if token:
            return f"{head}{marker}{token[:6]}…{sep}{rest}"
    return path


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        access_logger.info(
            "%s %s -> %s (%.1f ms) rid=%s",
            request.method,
            _redact(request.url.path),
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
