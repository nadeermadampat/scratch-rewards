"""YouTube channel-subscription provider.

Two verification modes (set in app_config.yaml -> providers.youtube.verification_mode):

* ``simulated`` (MVP default): the user attests that they subscribed. This is NOT
  proof — a redirect or a button click cannot prove a subscription — and results are
  stored with method="simulated" so they can be told apart later.
* ``oauth``: the user grants `youtube.readonly`; we call
  ``subscriptions.list(mine=true, forChannelId=...)`` on their behalf. Implemented
  against the documented API but not yet exercised against live Google endpoints,
  and the frontend redirect/callback is not wired up.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.models.enums import VerificationStatus
from app.providers.base import (
    EngagementTarget,
    PlatformInfo,
    SocialMediaProvider,
    VerificationRequest,
    VerificationResult,
)

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SUBSCRIPTIONS_URL = "https://www.googleapis.com/youtube/v3/subscriptions"
READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class YouTubeProvider(SocialMediaProvider):
    key = "youtube"

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            key=self.key,
            display_name="YouTube",
            action_label="Subscribe",
            brand_color="#ff0033",
            enabled=self.config.enabled,
            verification_mode=self.config.verification_mode,
        )

    def get_engagement_target(self, platform_config: dict[str, Any]) -> EngagementTarget:
        channel_id = platform_config.get("channel_id")
        base = platform_config.get("channel_url") or (
            f"https://www.youtube.com/channel/{channel_id}" if channel_id else "https://www.youtube.com"
        )
        separator = "&" if "?" in base else "?"
        name = platform_config.get("channel_name") or "our channel"
        return EngagementTarget(
            # sub_confirmation=1 makes YouTube open its own "Confirm subscription" prompt.
            url=f"{base}{separator}sub_confirmation=1",
            title=name,
            handle=base.rsplit("/", 1)[-1] if "/@" in base else None,
            instructions=[
                f"Tap Subscribe to open {name} on YouTube.",
                "Confirm the subscription in YouTube, then come back to this page.",
                "Verify to receive your scratch card.",
            ],
        )

    def start_verification(self, platform_config: dict[str, Any], redirect_uri: str, state: str) -> str | None:
        if self.config.verification_mode != "oauth":
            return None
        query = urlencode(
            {
                "client_id": self.settings.youtube_oauth_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": READONLY_SCOPE,
                "state": state,
                "access_type": "online",
            }
        )
        return f"{GOOGLE_AUTH_URL}?{query}"

    def verify(self, request: VerificationRequest) -> VerificationResult:
        if self.config.verification_mode == "oauth":
            return self._verify_oauth(request)
        return self._verify_simulated(request)

    # -- modes ------------------------------------------------------------

    def _verify_simulated(self, request: VerificationRequest) -> VerificationResult:
        if request.proof.get("attested") is True:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="simulated",
                detail="Simulated verification: user attested to subscribing.",
            )
        return VerificationResult(
            status=VerificationStatus.FAILED,
            method="simulated",
            detail="Please subscribe to the channel and confirm before verifying.",
        )

    def _verify_oauth(self, request: VerificationRequest) -> VerificationResult:
        code = request.proof.get("oauth_code")
        redirect_uri = request.proof.get("redirect_uri")
        channel_id = request.platform_config.get("channel_id")
        if not (code and redirect_uri and channel_id):
            return self._failed("Google authorization is required to verify the subscription.")
        try:
            with httpx.Client(timeout=10) as client:
                token_response = client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.youtube_oauth_client_id,
                        "client_secret": self.settings.youtube_oauth_client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                token_response.raise_for_status()
                access_token = token_response.json()["access_token"]
                response = client.get(
                    SUBSCRIPTIONS_URL,
                    params={"part": "snippet", "mine": "true", "forChannelId": channel_id},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                items = response.json().get("items", [])
        except (httpx.HTTPError, KeyError, ValueError):
            logger.exception("YouTube subscription check failed")
            return self._failed("We could not reach YouTube to verify your subscription. Please try again.")
        if not items:
            return self._failed("We could not find a subscription to the channel on this Google account.")
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="oauth",
            platform_user_id=items[0].get("snippet", {}).get("channelId"),
        )

    @staticmethod
    def _failed(detail: str) -> VerificationResult:
        return VerificationResult(status=VerificationStatus.FAILED, method="oauth", detail=detail)
