"""Placeholders for platforms on the roadmap.

They are listed by `GET /api/social-platforms` as not-yet-available. To ship one,
subclass `SocialMediaProvider` in its own module (as `youtube.py` does), implement
`verify`, and replace the placeholder in `registry.py`.
"""
from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.providers.base import (
    EngagementTarget,
    PlatformInfo,
    SocialMediaProvider,
    VerificationRequest,
    VerificationResult,
)


class PlannedProvider(SocialMediaProvider):
    display_name = ""
    action_label = "Follow"
    brand_color = "#888888"

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            key=self.key,
            display_name=self.display_name,
            action_label=self.action_label,
            brand_color=self.brand_color,
            enabled=False,
            verification_mode="unavailable",
        )

    def get_engagement_target(self, platform_config: dict[str, Any]) -> EngagementTarget:
        return EngagementTarget(
            url=platform_config.get("profile_url", ""),
            title=platform_config.get("profile_name", self.display_name),
        )

    def verify(self, request: VerificationRequest) -> VerificationResult:
        raise AppError(501, "PLATFORM_NOT_AVAILABLE", f"{self.display_name} is not available yet.")


class InstagramProvider(PlannedProvider):
    key = "instagram"
    display_name = "Instagram"
    brand_color = "#e1306c"


class FacebookProvider(PlannedProvider):
    key = "facebook"
    display_name = "Facebook"
    brand_color = "#1877f2"


class TikTokProvider(PlannedProvider):
    key = "tiktok"
    display_name = "TikTok"
    brand_color = "#111111"
