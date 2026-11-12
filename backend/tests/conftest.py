from __future__ import annotations

import os

# Must be set before the app (and its cached settings) is imported.
os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL="sqlite://",
    ADMIN_API_KEY="test-admin-key",
    SECRET_KEY="test-secret",
    RATE_LIMIT_ENABLED="true",
    APP_BASE_URL="http://testserver",
    # Blank out anything a developer's local .env might set, so tests are repeatable.
    YOUTUBE_CHANNEL_ID="",
    YOUTUBE_CHANNEL_URL="",
    YOUTUBE_CHANNEL_NAME="",
    YOUTUBE_VERIFICATION_MODE="",
    YOUTUBE_OAUTH_CLIENT_ID="test-client-id",
    YOUTUBE_OAUTH_CLIENT_SECRET="test-client-secret",
    TRUST_FORWARDED_FOR="false",
)
os.environ.pop("YOUTUBE_AUTO_SUBSCRIBE", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import app
from app.models import Base, Campaign
from app.seed import seed_demo

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture(autouse=True)
def youtube():
    """The YouTube provider, reset to simulated mode around every test."""
    from app.providers import get_registry

    provider = get_registry().get("youtube")
    provider.mode, provider.auto_subscribe, provider.transport = "simulated", True, None
    yield provider
    provider.mode, provider.auto_subscribe, provider.transport = "simulated", True, None


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture()
def campaign(db) -> Campaign:
    created = seed_demo(db)
    assert created is not None
    return created


@pytest.fixture()
def client(session_factory, campaign):
    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def issue_card(client, campaign):
    """Run verify + issue and return the issued-card payload."""

    def _issue(device_id: str = "device-0000-0000-0001", **extra) -> dict:
        verify = client.post(
            "/api/subscriptions/verify",
            json={
                "campaign_id": campaign.slug,
                "device_id": device_id,
                "consent": True,
                "proof": {"attested": True},
                **extra,
            },
        )
        assert verify.status_code == 200, verify.text
        token = verify.json()["data"]["verification_token"]
        issued = client.post("/api/scratch-cards", json={"verification_token": token})
        assert issued.status_code == 201, issued.text
        return {**issued.json()["data"], "verification_token": token}

    return _issue
