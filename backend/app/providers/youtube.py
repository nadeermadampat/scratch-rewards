"""YouTube channel-subscription provider.

Verification modes (app_config.yaml -> providers.youtube.verification_mode, or the
YOUTUBE_VERIFICATION_MODE environment variable):

* ``simulated``: the participant attests that they subscribed. This is NOT proof — a
  redirect or a button click cannot prove a subscription — and results are stored with
  method="simulated" so they can be told apart later.
* ``oauth``: the participant signs in with Google. We ask YouTube whether that account
  is subscribed to the campaign's channel. With ``auto_subscribe`` on, an account that
  is not yet subscribed is subscribed through the API (the page tells the participant
  this before they sign in). The Google access token is used once and then revoked;
  it is never stored.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import ProviderConfig, Settings
from app.core.errors import AppError
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
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/youtube/v3"
READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
#: Needed to create a subscription on the participant's behalf.
MANAGE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"

_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_HANDLE_IN_URL = re.compile(r"/@([A-Za-z0-9._-]+)")


class _YouTubeApiError(Exception):
    def __init__(self, status: int, reason: str) -> None:
        super().__init__(f"{status} {reason}")
        self.status = status
        self.reason = reason


class YouTubeProvider(SocialMediaProvider):
    key = "youtube"

    def __init__(self, config: ProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        self.mode = settings.youtube_verification_mode or config.verification_mode
        self.auto_subscribe = (
            config.auto_subscribe if settings.youtube_auto_subscribe is None else settings.youtube_auto_subscribe
        )
        #: Replaced in tests to answer Google's endpoints locally.
        self.transport: httpx.BaseTransport | None = None

    # -- interface --------------------------------------------------------

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            key=self.key,
            display_name="YouTube",
            action_label="Subscribe",
            brand_color="#ff0033",
            enabled=self.config.enabled,
            verification_mode=self.mode,
            auto_subscribe=self.mode == "oauth" and self.auto_subscribe,
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
        if self.mode != "oauth":
            return None
        if not (self.settings.youtube_oauth_client_id and self.settings.youtube_oauth_client_secret):
            raise AppError(503, "OAUTH_NOT_CONFIGURED", "Google sign-in is not set up for this site yet.")
        query = urlencode(
            {
                "client_id": self.settings.youtube_oauth_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": MANAGE_SCOPE if self.auto_subscribe else READONLY_SCOPE,
                "state": state,
                "access_type": "online",  # no refresh token: we never act for the user later
            }
        )
        return f"{GOOGLE_AUTH_URL}?{query}"

    def verify(self, request: VerificationRequest) -> VerificationResult:
        if self.mode == "oauth":
            return self._verify_oauth(request)
        return self._verify_simulated(request)

    # -- simulated --------------------------------------------------------

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

    # -- oauth ------------------------------------------------------------

    def _verify_oauth(self, request: VerificationRequest) -> VerificationResult:
        code = request.proof.get("oauth_code")
        redirect_uri = request.proof.get("redirect_uri")
        if not (code and redirect_uri):
            return self._failed("Please continue with Google to verify your subscription.")

        with httpx.Client(timeout=10, transport=self.transport) as client:
            try:
                access_token = self._exchange_code(client, code, redirect_uri)
            except (_YouTubeApiError, httpx.HTTPError, KeyError, ValueError):
                logger.warning("Google code exchange failed", exc_info=True)
                return self._failed("Google sign-in did not complete. Please try again.")

            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                return self._check_and_subscribe(client, headers, request.platform_config)
            except _YouTubeApiError as error:
                logger.warning("YouTube API error: %s", error)
                return self._failed(self._explain(error))
            except (httpx.HTTPError, KeyError, ValueError):
                logger.exception("YouTube subscription check failed")
                return self._failed("We couldn't reach YouTube. Please try again in a moment.")
            finally:
                self._revoke(client, access_token)

    def _check_and_subscribe(
        self, client: httpx.Client, headers: dict[str, str], platform_config: dict[str, Any]
    ) -> VerificationResult:
        channel_id = self._resolve_channel_id(client, headers, platform_config)
        if channel_id is None:
            logger.error("Campaign channel could not be resolved from %s", platform_config)
            return self._failed("This campaign's YouTube channel is not set up correctly.")

        me = self._get(client, headers, "channels", {"part": "id", "mine": "true"}).get("items", [])
        subscriber_id = me[0]["id"] if me else None

        existing = self._get(
            client, headers, "subscriptions", {"part": "snippet", "mine": "true", "forChannelId": channel_id}
        ).get("items", [])
        if existing:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="oauth",
                platform_user_id=subscriber_id or existing[0].get("snippet", {}).get("channelId"),
                detail="Already subscribed.",
            )

        if not self.auto_subscribe:
            return self._failed(
                "This Google account isn't subscribed to the channel yet. Subscribe on YouTube, then try again."
            )

        try:
            created = self._request(
                client, "POST", f"{API_BASE}/subscriptions", headers=headers, params={"part": "snippet"},
                json={"snippet": {"resourceId": {"kind": "youtube#channel", "channelId": channel_id}}},
            )
        except _YouTubeApiError as error:
            if error.reason != "subscriptionDuplicate":  # raced with a manual subscribe: fine
                raise
            created = {}
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="oauth_subscribe",
            platform_user_id=subscriber_id or created.get("snippet", {}).get("channelId"),
            detail="Subscribed through YouTube.",
        )

    def _resolve_channel_id(
        self, client: httpx.Client, headers: dict[str, str], platform_config: dict[str, Any]
    ) -> str | None:
        """Accept a real channel id (UC…), or look one up from the channel's @handle."""
        configured = str(platform_config.get("channel_id") or "").strip()
        if _CHANNEL_ID.match(configured):
            return configured
        in_url = _HANDLE_IN_URL.search(str(platform_config.get("channel_url") or ""))
        handle = in_url.group(1) if in_url else configured.lstrip("@")
        if not handle:
            return None
        items = self._get(client, headers, "channels", {"part": "id", "forHandle": f"@{handle}"}).get("items", [])
        return items[0]["id"] if items else None

    # -- http helpers -----------------------------------------------------

    def _exchange_code(self, client: httpx.Client, code: str, redirect_uri: str) -> str:
        payload = self._request(
            client, "POST", GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": self.settings.youtube_oauth_client_id,
                "client_secret": self.settings.youtube_oauth_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        return payload["access_token"]

    def _get(self, client: httpx.Client, headers: dict[str, str], resource: str, params: dict[str, str]) -> dict:
        return self._request(client, "GET", f"{API_BASE}/{resource}", headers=headers, params=params)

    @staticmethod
    def _request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> dict:
        response = client.request(method, url, **kwargs)
        if response.is_success:
            return response.json() if response.content else {}
        reason = "unknown"
        try:
            error = response.json().get("error", {})
            if isinstance(error, dict):
                reason = (error.get("errors") or [{}])[0].get("reason") or error.get("status") or reason
            else:  # token endpoint: {"error": "invalid_grant"}
                reason = str(error)
        except ValueError:
            pass
        raise _YouTubeApiError(response.status_code, reason)

    @staticmethod
    def _revoke(client: httpx.Client, access_token: str) -> None:
        """Give the access back straight away; we only needed it for this one check."""
        try:
            client.post(GOOGLE_REVOKE_URL, data={"token": access_token})
        except httpx.HTTPError:
            logger.warning("Could not revoke Google token", exc_info=True)

    @staticmethod
    def _explain(error: _YouTubeApiError) -> str:
        if error.reason in ("quotaExceeded", "rateLimitExceeded", "dailyLimitExceeded"):
            return "YouTube is busy right now. Please try again later."
        if error.reason in ("youtubeSignupRequired", "channelNotFound", "subscriberNotFound"):
            return "This Google account doesn't have a YouTube profile yet. Open YouTube once with it, then try again."
        if error.reason == "subscriptionForbidden":
            return "This account can't subscribe to the channel (you can't subscribe to your own channel)."
        if error.status in (401, 403):
            return "YouTube access wasn't granted. Please try again and allow the requested permission."
        return "We couldn't confirm your subscription with YouTube. Please try again."

    @staticmethod
    def _failed(detail: str) -> VerificationResult:
        return VerificationResult(status=VerificationStatus.FAILED, method="oauth", detail=detail)
