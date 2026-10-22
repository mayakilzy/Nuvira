"""Create the authoritative pre-SECURITY-01 application schema.

Revision ID: 0000_authoritative_schema
Revises: None

This revision reconstructs the schema historically created by
Base.metadata.create_all(). Existing databases already stamped at 0001 or 0002
do not execute it. Legacy unversioned databases must pass schema adoption
validation before being stamped at this revision.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0000_authoritative_schema"
down_revision = None
branch_labels = None
depends_on = None


def _index(table: str, column: str, *, unique: bool = False) -> None:
    op.create_index(f"ix_{table}_{column}", table, [column], unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        embedding_type = Vector(1536)
    else:
        embedding_type = sa.JSON()

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer()),
        sa.Column("admin_id", sa.Integer()),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("old_value", sa.JSON()),
        sa.Column("new_value", sa.JSON()),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("audit_log", "user_id")
    _index("audit_log", "admin_id")

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("price_monthly", sa.Integer(), nullable=False),
        sa.Column("price_yearly", sa.Integer(), nullable=False),
        sa.Column("stripe_price_id_monthly", sa.String(255)),
        sa.Column("stripe_price_id_yearly", sa.String(255)),
        sa.Column("provider_price_ids", sa.JSON(), nullable=False),
        sa.Column("credits_per_month", sa.Integer(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    _index("plans", "slug", unique=True)

    op.create_table(
        "subject_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("university", sa.String(255)),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("price_usd", sa.Float()),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("full_name", sa.String(255)),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("google_id", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("users", "email", unique=True)
    _index("users", "google_id", unique=True)

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("chapters", "subject_package_id")

    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("everyday_analogy", sa.Text()),
        sa.Column("mechanism_json", sa.JSON()),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("official_source_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("concepts", "subject_package_id")

    op.create_table(
        "avatar_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("current_shape", sa.String(30), nullable=False),
        sa.Column("current_color", sa.String(30), nullable=False),
        sa.Column("last_session_key", sa.String(64)),
        sa.Column("unlocked_shapes", sa.Text(), nullable=False),
        sa.Column("unlocked_colors", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("avatar_state", "user_id", unique=True)

    op.create_table(
        "credits_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(512)),
        sa.Column("reference_id", sa.String(255)),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("credits_ledger", "user_id")
    _index("credits_ledger", "reference_id")

    op.create_table(
        "phrase_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("phrase_index", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("phrase_usage", "user_id")
    _index("phrase_usage", "category")

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("subscriptions", "user_id")
    _index("subscriptions", "stripe_customer_id")
    _index("subscriptions", "stripe_subscription_id")

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("encrypted_key", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("user_api_keys", "user_id")

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ui_language", sa.String(5), nullable=False),
        sa.Column("theme", sa.String(10), nullable=False),
        sa.Column("avatar_corner_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("user_preferences", "user_id", unique=True)

    op.create_table(
        "user_subject_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("user_subject_access", "user_id")
    _index("user_subject_access", "subject_package_id")

    op.create_table(
        "fun_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("concept_id", sa.Integer(), sa.ForeignKey("concepts.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("fun_facts", "concept_id")

    op.create_table(
        "study_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("concept_id", sa.Integer(), sa.ForeignKey("concepts.id"), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("confidence_level", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("session_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("study_log", "user_id")
    _index("study_log", "concept_id")

    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_note", sa.String(500)),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("uploaded_documents", "uploaded_by_user_id")
    _index("uploaded_documents", "subject_package_id")
    _index("uploaded_documents", "chapter_id")

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer()),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id")),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id")),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("uploaded_documents.id")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("source_ref", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("user_id", "subject_package_id", "chapter_id", "document_id", "source_ref"):
        _index("embeddings", column)

    op.create_table(
        "fun_fact_shown_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("fun_fact_id", sa.Integer(), sa.ForeignKey("fun_facts.id"), nullable=False),
        sa.Column("shown_at_minute", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _index("fun_fact_shown_log", "user_id")
    _index("fun_fact_shown_log", "fun_fact_id")


def downgrade() -> None:
    for table in (
        "fun_fact_shown_log", "embeddings", "uploaded_documents", "study_log",
        "fun_facts", "user_subject_access", "user_preferences", "user_api_keys",
        "subscriptions", "phrase_usage", "credits_ledger", "avatar_state",
        "concepts", "chapters", "users", "subject_packages", "plans", "audit_log",
    ):
        op.drop_table(table)

