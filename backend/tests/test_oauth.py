"""Google sign-in verification and one-click subscribe, against a fake Google."""
from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import select

from app.models import Campaign, ScratchCard, SubscriptionVerification, User, utcnow
from app.providers.youtube import MANAGE_SCOPE, READONLY_SCOPE

CAMPAIGN_CHANNEL = "UC_x5XG1OV2P6uZZ5FSM9Ttw"  # from the seed config


class FakeGoogle:
    """Answers the Google endpoints the provider calls and records what was asked."""

    def __init__(self) -> None:
        self.subscribed = False
        self.my_channel = "UCviewer000000000000000001"
        self.handles = {"@KodeKloud": "UCresolved0000000000000001"}
        self.insert_error: str | None = None
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        self.calls.append((request.method, request.url.path, params))
        path = request.url.path
        if path == "/token":
            form = parse_qs(request.content.decode())
            if form["code"] == ["bad-code"]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            assert form["client_secret"] == ["test-client-secret"]
            assert form["redirect_uri"] == ["http://testserver/oauth/callback"]
            return httpx.Response(200, json={"access_token": "access-1"})
        if path == "/revoke":
            return httpx.Response(200, json={})
        assert request.headers["authorization"] == "Bearer access-1"
        if path.endswith("/channels"):
            if "forHandle" in params:
                found = self.handles.get(params["forHandle"])
                return httpx.Response(200, json={"items": [{"id": found}] if found else []})
            return httpx.Response(200, json={"items": [{"id": self.my_channel}]})
        if path.endswith("/subscriptions") and request.method == "GET":
            self.checked_channel = params["forChannelId"]
            items = [{"snippet": {"channelId": self.my_channel}}] if self.subscribed else []
            return httpx.Response(200, json={"items": items})
        if path.endswith("/subscriptions") and request.method == "POST":
            if self.insert_error:
                return httpx.Response(403, json={"error": {"errors": [{"reason": self.insert_error}]}})
            self.subscribed = True
            return httpx.Response(200, json={"snippet": {"channelId": self.my_channel}})
        return httpx.Response(404, json={})

    def count(self, method: str, suffix: str) -> int:
        return sum(1 for m, path, _ in self.calls if m == method and path.endswith(suffix))


@pytest.fixture()
def google(youtube) -> FakeGoogle:
    fake = FakeGoogle()
    youtube.mode = "oauth"
    youtube.auto_subscribe = True
    youtube.transport = httpx.MockTransport(fake)
    return fake


def _authorize(client, campaign, device_id="device-oauth-0000-0001", **extra) -> dict:
    response = client.post(
        "/api/subscriptions/authorize",
        json={"campaign_id": campaign.slug, "device_id": device_id, "consent": True, **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _complete(client, state: str, code: str = "good-code"):
    return client.post("/api/subscriptions/oauth/complete", json={"state": state, "code": code})


def test_authorize_builds_the_google_url(client, campaign, google):
    data = _authorize(client, campaign)
    url = urlparse(data["authorization_url"])
    query = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == ["http://testserver/oauth/callback"]
    assert query["scope"] == [MANAGE_SCOPE]
    assert query["state"] == [data["state"]]
    assert query["access_type"] == ["online"]
    assert len(data["state"]) >= 43


def test_read_only_mode_asks_for_the_read_only_scope(client, campaign, google, youtube):
    youtube.auto_subscribe = False
    query = parse_qs(urlparse(_authorize(client, campaign)["authorization_url"]).query)
    assert query["scope"] == [READONLY_SCOPE]
    assert client.get(f"/api/campaigns/{campaign.slug}").json()["data"]["platform"]["auto_subscribe"] is False


def test_campaign_reports_oauth_mode(client, campaign, google):
    platform = client.get(f"/api/campaigns/{campaign.slug}").json()["data"]["platform"]
    assert platform["verification_mode"] == "oauth"
    assert platform["auto_subscribe"] is True


def test_authorize_needs_consent_and_oauth_mode(client, campaign, google, youtube):
    no_consent = client.post("/api/subscriptions/authorize", json={"campaign_id": campaign.slug, "consent": False})
    assert no_consent.json()["error"]["code"] == "CONSENT_REQUIRED"
    youtube.mode = "simulated"
    simulated = client.post("/api/subscriptions/authorize", json={"campaign_id": campaign.slug, "consent": True})
    assert simulated.status_code == 409
    assert simulated.json()["error"]["code"] == "SIGN_IN_NOT_REQUIRED"


def test_authorize_fails_clearly_without_credentials(client, campaign, google, youtube, monkeypatch):
    monkeypatch.setattr(youtube.settings, "youtube_oauth_client_id", "")
    response = client.post("/api/subscriptions/authorize", json={"campaign_id": campaign.slug, "consent": True})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OAUTH_NOT_CONFIGURED"


def test_already_subscribed_account_is_verified_without_subscribing(client, campaign, google, session_factory):
    google.subscribed = True
    data = _complete(client, _authorize(client, campaign)["state"]).json()["data"]
    assert data["status"] == "verified"
    assert data["method"] == "oauth"
    assert data["campaign_slug"] == campaign.slug
    assert google.checked_channel == CAMPAIGN_CHANNEL
    assert google.count("POST", "/subscriptions") == 0
    assert google.count("POST", "/revoke") == 1  # access handed back

    issued = client.post("/api/scratch-cards", json={"verification_token": data["verification_token"]})
    assert issued.status_code == 201
    with session_factory() as s:
        assert s.scalar(select(User.platform_user_id).where(User.platform_user_id.is_not(None))) == google.my_channel


def test_one_click_subscribe(client, campaign, google):
    data = _complete(client, _authorize(client, campaign)["state"]).json()["data"]
    assert data["status"] == "verified"
    assert data["method"] == "oauth_subscribe"
    assert google.count("POST", "/subscriptions") == 1
    assert google.subscribed is True
    assert google.count("POST", "/revoke") == 1


def test_read_only_mode_does_not_subscribe(client, campaign, google, youtube):
    youtube.auto_subscribe = False
    data = _complete(client, _authorize(client, campaign)["state"]).json()["data"]
    assert data["status"] == "failed"
    assert data["verification_token"] is None
    assert "isn't subscribed" in data["message"]
    assert google.count("POST", "/subscriptions") == 0


def test_state_is_single_use(client, campaign, google):
    state = _authorize(client, campaign)["state"]
    assert _complete(client, state).json()["data"]["status"] == "verified"
    replay = _complete(client, state)
    assert replay.status_code == 403
    assert replay.json()["error"]["code"] == "VERIFICATION_INVALID"
    assert google.count("POST", "/token") == 1  # the replay never reached Google


def test_unknown_and_expired_state(client, campaign, google, session_factory):
    assert _complete(client, "x" * 43).status_code == 403
    state = _authorize(client, campaign)["state"]
    with session_factory() as s:
        row = s.scalar(select(SubscriptionVerification).where(SubscriptionVerification.token == state))
        row.expires_at = utcnow() - timedelta(minutes=1)
        s.commit()
    expired = _complete(client, state)
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "VERIFICATION_EXPIRED"
    assert google.calls == []


def test_oauth_state_cannot_be_used_as_a_card_token(client, campaign, google):
    state = _authorize(client, campaign)["state"]
    response = client.post("/api/scratch-cards", json={"verification_token": state})
    assert response.status_code == 403


def test_rejected_google_code(client, campaign, google):
    data = _complete(client, _authorize(client, campaign)["state"], code="bad-code").json()["data"]
    assert data["status"] == "failed"
    assert data["verification_token"] is None
    assert google.count("GET", "/subscriptions") == 0


def test_youtube_refusal_is_explained(client, campaign, google):
    google.insert_error = "subscriptionForbidden"
    data = _complete(client, _authorize(client, campaign)["state"]).json()["data"]
    assert data["status"] == "failed"
    assert "own channel" in data["message"]
    assert google.count("POST", "/revoke") == 1


def test_handle_is_resolved_to_a_channel_id(client, campaign, google, session_factory):
    with session_factory() as s:
        row = s.get(Campaign, campaign.id)
        row.platform_config = {"channel_id": "KodeKloud", "channel_url": "https://www.youtube.com/@KodeKloud"}
        s.commit()
    data = _complete(client, _authorize(client, campaign)["state"]).json()["data"]
    assert data["status"] == "verified"
    assert google.checked_channel == "UCresolved0000000000000001"


def test_same_youtube_account_gets_one_card_across_browsers(client, campaign, google, session_factory):
    tokens = []
    for device in ("device-oauth-aaaa-0001", "device-oauth-bbbb-0002"):
        verified = _complete(client, _authorize(client, campaign, device_id=device)["state"]).json()["data"]
        issued = client.post("/api/scratch-cards", json={"verification_token": verified["verification_token"]})
        tokens.append(issued.json()["data"])
    assert tokens[0]["token"] == tokens[1]["token"]
    assert tokens[1]["existing"] is True
    with session_factory() as s:
        assert len(s.scalars(select(ScratchCard)).all()) == 1

    google.my_channel = "UCviewer000000000000000002"  # a different person
    google.subscribed = False
    other = _complete(client, _authorize(client, campaign, device_id="device-oauth-cccc-0003")["state"]).json()["data"]
    issued = client.post("/api/scratch-cards", json={"verification_token": other["verification_token"]})
    assert issued.json()["data"]["token"] != tokens[0]["token"]


def test_attestation_is_not_accepted_in_oauth_mode(client, campaign, google):
    response = client.post(
        "/api/subscriptions/verify",
        json={"campaign_id": campaign.slug, "consent": True, "proof": {"attested": True}},
    )
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert data["verification_token"] is None
    assert google.calls == []
