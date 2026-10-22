"""Add SECURITY-01 session, commerce and cleanup controls.

Revision ID: 0002_security_controls
Revises: 0001_lowercase_emails

This is an additive upgrade after the reconstructed authoritative baseline and
email-normalization revision.
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_security_controls"
down_revision = "0001_lowercase_emails"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", sa.String(36)),
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"], unique=True)
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("return_path", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_oauth_states_state_hash", "oauth_states", ["state_hash"], unique=True)
    op.create_table(
        "oauth_exchanges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("return_path", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_oauth_exchanges_code_hash", "oauth_exchanges", ["code_hash"], unique=True)
    op.create_index("ix_oauth_exchanges_user_id", "oauth_exchanges", ["user_id"])
    op.create_table(
        "credit_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_price_id", sa.String(255), nullable=False, unique=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_credit_packs_slug", "credit_packs", ["slug"], unique=True)
    op.create_index("ix_credit_packs_provider", "credit_packs", ["provider"])
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_event_provider_id"),
    )
    op.create_index("ix_payment_events_user_id", "payment_events", ["user_id"])
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_account_deletion_requests_user_id", "account_deletion_requests", ["user_id"])
    op.add_column("uploaded_documents", sa.Column("error_code", sa.String(50)))
    op.add_column("uploaded_documents", sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("uploaded_documents", sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(
        "ix_embeddings_subject_owner_chapter_document",
        "embeddings", ["subject_package_id", "user_id", "chapter_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_embeddings_subject_owner_chapter_document", table_name="embeddings")
    op.drop_column("uploaded_documents", "processing_attempts")
    op.drop_column("uploaded_documents", "file_size")
    op.drop_column("uploaded_documents", "error_code")
    op.drop_table("account_deletion_requests")
    op.drop_table("payment_events")
    op.drop_table("credit_packs")
    op.drop_table("oauth_exchanges")
    op.drop_table("oauth_states")
    op.drop_table("refresh_sessions")
