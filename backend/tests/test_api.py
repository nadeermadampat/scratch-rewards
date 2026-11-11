"""End-to-end API tests for the participant journey and its abuse cases."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.models import AuditEvent, Campaign, Reward, ScratchCard, utcnow
from app.models.enums import CampaignStatus
from tests.conftest import ADMIN_HEADERS


def _card_row(session_factory, token: str) -> ScratchCard:
    with session_factory() as s:
        return s.scalar(select(ScratchCard).where(ScratchCard.token == token))


# -- catalogue ------------------------------------------------------------

def test_campaign_details_by_slug_and_id(client, campaign):
    for key in (campaign.slug, campaign.id):
        body = client.get(f"/api/campaigns/{key}").json()
        assert body["success"] is True
        data = body["data"]
        assert data["is_open"] is True
        assert data["platform"]["key"] == "youtube"
        assert data["platform"]["verification_mode"] == "simulated"
        assert "sub_confirmation=1" in data["engagement"]["url"]
        # Prize names are public; odds and the no-prize outcome are not.
        assert "Better luck next time" not in [p["name"] for p in data["prizes"]]
        assert "weight" not in str(data)


def test_unknown_campaign_uses_the_error_envelope(client):
    response = client.get("/api/campaigns/nope")
    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "CAMPAIGN_NOT_FOUND", "message": "This campaign does not exist.", "details": None},
    }


def test_platform_list_marks_future_platforms_unavailable(client):
    platforms = {p["key"]: p for p in client.get("/api/social-platforms").json()["data"]}
    assert platforms["youtube"]["enabled"] is True
    for key in ("instagram", "facebook", "tiktok"):
        assert platforms[key]["enabled"] is False


def test_reward_details_do_not_include_probability(client, db, campaign):
    reward = db.scalar(select(Reward).where(Reward.campaign_id == campaign.id))
    data = client.get(f"/api/rewards/{reward.id}").json()["data"]
    assert data["name"] == reward.name
    assert "weight" not in data
    assert client.get("/api/rewards/missing").status_code == 404


# -- verification ---------------------------------------------------------

def test_verification_requires_consent(client, campaign):
    response = client.post(
        "/api/subscriptions/verify",
        json={"campaign_id": campaign.slug, "consent": False, "proof": {"attested": True}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_click_alone_does_not_verify(client, campaign):
    response = client.post(
        "/api/subscriptions/verify", json={"campaign_id": campaign.slug, "consent": True}
    )
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert data["verification_token"] is None


def test_input_validation_errors_are_consistent(client, campaign):
    response = client.post(
        "/api/subscriptions/verify",
        json={"campaign_id": campaign.slug, "consent": True, "email": "not-an-email"},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "email"


def test_inactive_campaign_issues_nothing(client, campaign, session_factory):
    with session_factory() as s:
        s.get(Campaign, campaign.id).status = CampaignStatus.PAUSED
        s.commit()
    response = client.post(
        "/api/subscriptions/verify",
        json={"campaign_id": campaign.slug, "consent": True, "proof": {"attested": True}},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CAMPAIGN_NOT_ACTIVE"


def test_campaign_paused_between_verify_and_issue(client, campaign, session_factory):
    token = client.post(
        "/api/subscriptions/verify",
        json={"campaign_id": campaign.slug, "consent": True, "proof": {"attested": True}},
    ).json()["data"]["verification_token"]
    with session_factory() as s:
        s.get(Campaign, campaign.id).status = CampaignStatus.ENDED
        s.commit()
    response = client.post("/api/scratch-cards", json={"verification_token": token})
    assert response.status_code == 409


def test_card_cannot_be_issued_without_a_real_verification(client):
    response = client.post("/api/scratch-cards", json={"verification_token": "x" * 43})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


# -- card lifecycle -------------------------------------------------------

def test_full_journey(client, issue_card, session_factory):
    issued = issue_card(name="Asha", email="asha@example.com")
    token = issued["token"]
    assert issued["url"] == f"http://testserver/s/{token}"
    assert issued["existing"] is False
    assigned = _card_row(session_factory, token).reward_id

    opened = client.get(f"/api/scratch-cards/{token}").json()["data"]
    assert opened["status"] == "opened"
    assert opened["reward"] is None and opened["claim_reference"] is None

    started = client.post(f"/api/scratch-cards/{token}/start").json()["data"]
    assert started["status"] == "scratching"
    assert started["reward"]["id"] == assigned
    assert started["claim_reference"] is None

    done = client.post(f"/api/scratch-cards/{token}/complete").json()["data"]
    assert done["status"] == "completed"
    assert done["already_completed"] is False
    assert done["reward"]["id"] == assigned
    assert done["claim_reference"].startswith("SCR-")

    row = _card_row(session_factory, token)
    assert row.first_accessed_at and row.scratch_started_at and row.scratch_completed_at
    assert row.first_accessed_at <= row.scratch_started_at <= row.scratch_completed_at


def test_reward_is_fixed_at_generation_and_hidden_until_scratched(client, issue_card, session_factory):
    token = issue_card()["token"]
    assigned = _card_row(session_factory, token).reward_id
    assert assigned  # chosen before the card was ever opened

    # Refreshing an unscratched card never leaks or changes the reward.
    for _ in range(5):
        data = client.get(f"/api/scratch-cards/{token}").json()["data"]
        assert data["reward"] is None
    assert _card_row(session_factory, token).reward_id == assigned

    # Refreshing mid-scratch and after completion always shows the same reward.
    client.post(f"/api/scratch-cards/{token}/start")
    seen = {client.get(f"/api/scratch-cards/{token}").json()["data"]["reward"]["id"] for _ in range(3)}
    client.post(f"/api/scratch-cards/{token}/complete")
    seen.add(client.get(f"/api/scratch-cards/{token}").json()["data"]["reward"]["id"])
    assert seen == {assigned}


def test_duplicate_completion_is_idempotent_and_audited(client, issue_card, session_factory):
    token = issue_card()["token"]
    first = client.post(f"/api/scratch-cards/{token}/complete").json()["data"]
    completed_at = _card_row(session_factory, token).scratch_completed_at

    for _ in range(3):
        again = client.post(f"/api/scratch-cards/{token}/complete")
        assert again.status_code == 200
        data = again.json()["data"]
        assert data["already_completed"] is True
        assert data["claim_reference"] == first["claim_reference"]
        assert data["reward"]["id"] == first["reward"]["id"]

    assert _card_row(session_factory, token).scratch_completed_at == completed_at
    with session_factory() as s:
        events = s.scalars(select(AuditEvent.event_type)).all()
    assert events.count("card.completed") == 1
    assert events.count("card.duplicate_completion") == 3


def test_replaying_a_verification_returns_the_same_card(client, issue_card, session_factory):
    issued = issue_card()
    replay = client.post("/api/scratch-cards", json={"verification_token": issued["verification_token"]})
    assert replay.json()["data"]["token"] == issued["token"]
    assert replay.json()["data"]["existing"] is True
    with session_factory() as s:
        assert len(s.scalars(select(ScratchCard)).all()) == 1


def test_one_card_per_participant(client, issue_card, session_factory):
    first = issue_card(device_id="device-aaaa-bbbb-0001")
    second = issue_card(device_id="device-aaaa-bbbb-0001")  # verifies again from the same browser
    assert second["token"] == first["token"]
    assert second["existing"] is True
    other = issue_card(device_id="device-aaaa-bbbb-0002")
    assert other["token"] != first["token"]


def test_expired_card(client, issue_card, session_factory):
    token = issue_card()["token"]
    with session_factory() as s:
        card = s.scalar(select(ScratchCard).where(ScratchCard.token == token))
        card.expires_at = utcnow() - timedelta(minutes=1)
        s.commit()

    view = client.get(f"/api/scratch-cards/{token}").json()["data"]
    assert view["status"] == "expired"
    assert view["reward"] is None
    for action in ("start", "complete"):
        response = client.post(f"/api/scratch-cards/{token}/{action}")
        assert response.status_code == 410
        assert response.json()["error"]["code"] == "CARD_EXPIRED"
    assert _card_row(session_factory, token).claim_reference is None


def test_completed_card_does_not_expire(client, issue_card, session_factory):
    token = issue_card()["token"]
    client.post(f"/api/scratch-cards/{token}/complete")
    with session_factory() as s:
        s.scalar(select(ScratchCard).where(ScratchCard.token == token)).expires_at = utcnow() - timedelta(days=1)
        s.commit()
    assert client.get(f"/api/scratch-cards/{token}").json()["data"]["status"] == "completed"


def test_invalid_tokens(client):
    for token in ("abc", "A" * 43, "not_a_real_token_but_long_enough_to_pass_format"):
        for method, path in (
            ("get", f"/api/scratch-cards/{token}"),
            ("post", f"/api/scratch-cards/{token}/start"),
            ("post", f"/api/scratch-cards/{token}/complete"),
        ):
            response = getattr(client, method)(path)
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "CARD_NOT_FOUND"


def test_rate_limit_on_verification(client, campaign):
    payload = {"campaign_id": campaign.slug, "consent": True}
    statuses = [client.post("/api/subscriptions/verify", json=payload).status_code for _ in range(12)]
    assert statuses[:10] == [200] * 10
    assert statuses[10:] == [429, 429]
    limited = client.post("/api/subscriptions/verify", json=payload)
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) > 0


# -- admin ----------------------------------------------------------------

def test_admin_requires_key(client):
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/admin/overview", headers=ADMIN_HEADERS).status_code == 200


def test_admin_overview_counts(client, issue_card, campaign):
    done = issue_card(device_id="device-admin-0000-0001", name="Asha")
    issue_card(device_id="device-admin-0000-0002")
    completed = client.post(f"/api/scratch-cards/{done['token']}/complete").json()["data"]

    data = client.get(f"/api/admin/overview?campaign_id={campaign.id}", headers=ADMIN_HEADERS).json()["data"]
    stats = data["stats"]
    assert stats["total_users"] == 2
    assert stats["cards_generated"] == 2
    assert stats["cards_scratched"] == 1
    assert stats["rewards_distributed"] == (1 if completed["reward"]["is_prize"] else 0)
    assert sum(row["assigned"] for row in data["distribution"]) == 2
    assert sum(row["revealed"] for row in data["distribution"]) == 1
    assert abs(sum(row["configured_share"] for row in data["distribution"]) - 1) < 1e-9

    by_status = {row["status"]: row for row in data["recent_activity"]}
    assert by_status["completed"]["reward_name"] == completed["reward"]["name"]
    assert by_status["completed"]["user_label"] == "Asha"
    assert by_status["issued"]["reward_name"] is None  # unrevealed outcomes stay hidden


def test_admin_can_tune_rewards_without_touching_issued_cards(client, issue_card, campaign, session_factory):
    token = issue_card()["token"]
    assigned = _card_row(session_factory, token).reward_id

    rewards = client.get(f"/api/admin/campaigns/{campaign.id}/rewards", headers=ADMIN_HEADERS).json()["data"]
    for reward in rewards:
        response = client.patch(
            f"/api/admin/rewards/{reward['id']}", headers=ADMIN_HEADERS, json={"weight": 0, "is_active": False}
        )
        assert response.json()["data"]["is_active"] is False
    created = client.post(
        f"/api/admin/campaigns/{campaign.id}/rewards",
        headers=ADMIN_HEADERS,
        json={"name": "Only Prize", "weight": 1},
    )
    assert created.status_code == 201

    assert _card_row(session_factory, token).reward_id == assigned
    fresh = issue_card(device_id="device-tune-0000-0002")["token"]
    done = client.post(f"/api/scratch-cards/{fresh}/complete").json()["data"]
    assert done["reward"]["name"] == "Only Prize"

    bad = client.patch(f"/api/admin/rewards/{rewards[0]['id']}", headers=ADMIN_HEADERS, json={"weight": -1})
    assert bad.status_code == 422


def test_admin_pause_and_redeem(client, issue_card, campaign, session_factory):
    token = issue_card()["token"]
    with session_factory() as s:
        prize = s.scalar(select(Reward).where(Reward.campaign_id == campaign.id, Reward.is_prize.is_(True)))
        s.scalar(select(ScratchCard).where(ScratchCard.token == token)).reward_id = prize.id
        s.commit()
    reference = client.post(f"/api/scratch-cards/{token}/complete").json()["data"]["claim_reference"]

    redeemed = client.post("/api/admin/redemptions", headers=ADMIN_HEADERS, json={"claim_reference": reference})
    assert redeemed.json()["data"]["redemption_status"] == "redeemed"
    twice = client.post("/api/admin/redemptions", headers=ADMIN_HEADERS, json={"claim_reference": reference})
    assert twice.status_code == 409
    assert twice.json()["error"]["code"] == "ALREADY_REDEEMED"

    paused = client.patch(f"/api/admin/campaigns/{campaign.id}", headers=ADMIN_HEADERS, json={"status": "paused"})
    assert paused.json()["data"]["status"] == "paused"
    assert client.get(f"/api/campaigns/{campaign.slug}").json()["data"]["is_open"] is False
