"""The contract every social media integration implements.

Nothing outside `app.providers` knows about a specific platform: services ask the
registry for a provider by key and talk to it only through this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import ProviderConfig, Settings
from app.models.enums import VerificationStatus


@dataclass(frozen=True)
class PlatformInfo:
    """Static, display-oriented details about a platform."""

    key: str
    display_name: str
    action_label: str       # e.g. "Subscribe", "Follow"
    brand_color: str
    enabled: bool
    verification_mode: str  # "simulated", "oauth", "unavailable"


@dataclass(frozen=True)
class EngagementTarget:
    """Where to send the user, for a given campaign's platform_config."""

    url: str
    title: str
    handle: str | None = None
    instructions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationRequest:
    platform_config: dict[str, Any]
    #: Provider-specific evidence from the client (attestation, OAuth code, ...).
    proof: dict[str, Any]


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    method: str
    platform_user_id: str | None = None
    detail: str | None = None


class SocialMediaProvider(ABC):
    key: str

    def __init__(self, config: ProviderConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    @abstractmethod
    def info(self) -> PlatformInfo:
        """Display details for this platform."""

    @abstractmethod
    def get_engagement_target(self, platform_config: dict[str, Any]) -> EngagementTarget:
        """URL and copy for the page the user must subscribe to / follow."""

    def start_verification(self, platform_config: dict[str, Any], redirect_uri: str, state: str) -> str | None:
        """Return an authorization URL if the provider needs a redirect step, else None."""
        return None

    @abstractmethod
    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Decide whether the user completed the engagement action."""
