"""Configuration: secrets from the environment, everything else from YAML."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Environment-driven settings (see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./scratch_rewards.db"
    app_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    secret_key: str = "dev-only-secret"
    admin_api_key: str = ""
    rate_limit_enabled: bool = True
    #: Take the client IP from X-Forwarded-For. Enable only behind a proxy that
    #: sets the header itself (e.g. Vercel); otherwise clients could spoof it.
    trust_forwarded_for: bool = False
    app_config_path: str = str(BACKEND_DIR / "config" / "app_config.yaml")

    youtube_channel_id: str = ""
    youtube_channel_url: str = ""
    youtube_channel_name: str = ""
    youtube_api_key: str = ""
    youtube_oauth_client_id: str = ""
    youtube_oauth_client_secret: str = ""
    #: Optional overrides of providers.youtube in app_config.yaml, so a deployment
    #: can switch modes without a code change.
    youtube_verification_mode: str = ""
    youtube_auto_subscribe: bool | None = None

    @field_validator("database_url")
    @classmethod
    def _anchor_sqlite_path(cls, url: str) -> str:
        """Resolve `sqlite:///./file.db` against backend/, not the current directory."""
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            return f"sqlite:///{(BACKEND_DIR / url[len(prefix):]).as_posix()}"
        # Hosted Postgres providers hand out postgres:// or postgresql:// URLs;
        # SQLAlchemy needs the driver named explicitly.
        for scheme in ("postgres://", "postgresql://"):
            if url.startswith(scheme):
                return "postgresql+psycopg://" + url[len(scheme):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class ScratchCardConfig(BaseModel):
    expiry_hours: int = Field(72, gt=0)
    reveal_threshold: float = Field(0.5, gt=0, le=1)
    max_cards_per_user: int = Field(1, ge=1)


class VerificationConfig(BaseModel):
    token_ttl_minutes: int = Field(15, gt=0)
    #: How long a participant has to finish the sign-in redirect.
    oauth_state_ttl_minutes: int = Field(10, gt=0)


class RateLimitRule(BaseModel):
    limit: int = Field(gt=0)
    window_seconds: int = Field(gt=0)


class ProviderConfig(BaseModel):
    enabled: bool = False
    verification_mode: str = "simulated"
    auto_subscribe: bool = False


class AppConfig(BaseModel):
    """Non-sensitive settings loaded from `config/app_config.yaml`."""

    scratch_card: ScratchCardConfig = ScratchCardConfig()
    verification: VerificationConfig = VerificationConfig()
    rate_limits: dict[str, RateLimitRule] = {}
    providers: dict[str, ProviderConfig] = {}
    seed: dict[str, Any] = {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_app_config() -> AppConfig:
    path = Path(get_settings().app_config_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return AppConfig.model_validate(raw or {})
