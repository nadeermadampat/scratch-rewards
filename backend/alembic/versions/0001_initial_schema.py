"""Initial schema: clients, campaigns, users, rewards, verifications, scratch cards, audit.

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _ts(name: str, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("tagline", sa.String(240)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("brand", sa.JSON, nullable=False),
        _ts("created_at", nullable=False),
    )
    op.create_index("ix_clients_slug", "clients", ["slug"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("headline", sa.String(240)),
        sa.Column("description", sa.Text),
        sa.Column("terms", sa.Text),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("platform_config", sa.JSON, nullable=False),
        sa.Column("settings", sa.JSON, nullable=False),
        _ts("starts_at"),
        _ts("ends_at"),
        sa.Column("status", sa.String(20), nullable=False),
        _ts("created_at", nullable=False),
        _ts("updated_at", nullable=False),
    )
    op.create_index("ix_campaigns_client_id", "campaigns", ["client_id"])
    op.create_index("ix_campaigns_slug", "campaigns", ["slug"], unique=True)
    op.create_index("ix_campaigns_platform", "campaigns", ["platform"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("anonymous_id", sa.String(64)),
        sa.Column("name", sa.String(120)),
        sa.Column("email", sa.String(254)),
        sa.Column("phone", sa.String(32)),
        sa.Column("platform", sa.String(40)),
        sa.Column("platform_user_id", sa.String(160)),
        _ts("consent_at"),
        _ts("created_at", nullable=False),
    )
    op.create_index("ix_users_anonymous_id", "users", ["anonymous_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_platform_user_id", "users", ["platform_user_id"])

    op.create_table(
        "rewards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reward_type", sa.String(20), nullable=False),
        sa.Column("value", sa.String(60)),
        sa.Column("icon", sa.String(16)),
        sa.Column("weight", sa.Float, nullable=False),
        sa.Column("is_prize", sa.Boolean, nullable=False),
        sa.Column("total_quantity", sa.Integer),
        sa.Column("issued_count", sa.Integer, nullable=False),
        sa.Column("redemption_instructions", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        _ts("created_at", nullable=False),
    )
    op.create_index("ix_rewards_campaign_id", "rewards", ["campaign_id"])

    op.create_table(
        "subscription_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("method", sa.String(40), nullable=False),
        sa.Column("detail", sa.Text),
        sa.Column("token", sa.String(128)),
        _ts("expires_at"),
        _ts("verified_at"),
        _ts("consumed_at"),
        _ts("created_at", nullable=False),
    )
    op.create_index("ix_subscription_verifications_campaign_id", "subscription_verifications", ["campaign_id"])
    op.create_index("ix_subscription_verifications_user_id", "subscription_verifications", ["user_id"])
    op.create_index("ix_subscription_verifications_token", "subscription_verifications", ["token"], unique=True)

    op.create_table(
        "scratch_cards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("reward_id", sa.String(36), sa.ForeignKey("rewards.id"), nullable=False),
        sa.Column("verification_id", sa.String(36), sa.ForeignKey("subscription_verifications.id")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("claim_reference", sa.String(24)),
        sa.Column("redemption_status", sa.String(20), nullable=False),
        _ts("generated_at", nullable=False),
        _ts("first_accessed_at"),
        _ts("scratch_started_at"),
        _ts("scratch_completed_at"),
        _ts("redeemed_at"),
        _ts("expires_at", nullable=False),
        sa.UniqueConstraint("verification_id", name="uq_scratch_cards_verification_id"),
    )
    op.create_index("ix_scratch_cards_token", "scratch_cards", ["token"], unique=True)
    op.create_index("ix_scratch_cards_user_id", "scratch_cards", ["user_id"])
    op.create_index("ix_scratch_cards_campaign_id", "scratch_cards", ["campaign_id"])
    op.create_index("ix_scratch_cards_reward_id", "scratch_cards", ["reward_id"])
    op.create_index("ix_scratch_cards_status", "scratch_cards", ["status"])
    op.create_index("ix_scratch_cards_claim_reference", "scratch_cards", ["claim_reference"], unique=True)
    op.create_index("ix_scratch_cards_generated_at", "scratch_cards", ["generated_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("campaign_id", sa.String(36)),
        sa.Column("user_id", sa.String(36)),
        sa.Column("scratch_card_id", sa.String(36)),
        sa.Column("ip_hash", sa.String(64)),
        sa.Column("user_agent", sa.String(300)),
        sa.Column("payload", sa.JSON, nullable=False),
        _ts("created_at", nullable=False),
    )
    for column in ("event_type", "campaign_id", "user_id", "scratch_card_id", "ip_hash", "created_at"):
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])


def downgrade() -> None:
    for table in (
        "audit_events",
        "scratch_cards",
        "subscription_verifications",
        "rewards",
        "users",
        "campaigns",
        "clients",
    ):
        op.drop_table(table)
