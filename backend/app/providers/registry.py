"""Lookup of providers by platform key."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import ProviderConfig, get_app_config, get_settings
from app.core.errors import AppError
from app.providers.base import SocialMediaProvider
from app.providers.planned import FacebookProvider, InstagramProvider, TikTokProvider
from app.providers.youtube import YouTubeProvider

#: Add new provider classes here.
PROVIDER_CLASSES: tuple[type[SocialMediaProvider], ...] = (
    YouTubeProvider,
    InstagramProvider,
    FacebookProvider,
    TikTokProvider,
)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, SocialMediaProvider] = {}

    def register(self, provider: SocialMediaProvider) -> None:
        self._providers[provider.key] = provider

    def get(self, key: str) -> SocialMediaProvider:
        provider = self._providers.get(key)
        if provider is None:
            raise AppError(404, "PLATFORM_NOT_SUPPORTED", f"Unknown social platform '{key}'.")
        return provider

    def get_enabled(self, key: str) -> SocialMediaProvider:
        provider = self.get(key)
        if not provider.info().enabled:
            raise AppError(501, "PLATFORM_NOT_AVAILABLE", f"{provider.info().display_name} is not available yet.")
        return provider

    def all(self) -> list[SocialMediaProvider]:
        return list(self._providers.values())


@lru_cache
def get_registry() -> ProviderRegistry:
    settings = get_settings()
    configs = get_app_config().providers
    registry = ProviderRegistry()
    for provider_class in PROVIDER_CLASSES:
        config = configs.get(provider_class.key, ProviderConfig())
        registry.register(provider_class(config, settings))
    return registry
