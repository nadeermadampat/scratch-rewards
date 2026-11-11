"""FastAPI application factory."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, engagement, public
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, register_request_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Scratch Rewards API",
        version="0.1.0",
        description="Social media engagement campaigns with scratch card rewards.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )
    register_request_logging(app)
    register_error_handlers(app)

    for router in (public.router, engagement.router, admin.router):
        app.include_router(router, prefix="/api")

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"success": True, "data": {"status": "ok"}}

    if not settings.admin_api_key:
        logger.warning("ADMIN_API_KEY is not set: the admin API is disabled.")
    logger.info("Scratch Rewards API ready (environment=%s)", settings.environment)
    return app


app = create_app()
