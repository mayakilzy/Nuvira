"""Add universal curriculum library, resources, lessons and enrollment controls.

Revision ID: 0003_curriculum_library
Revises: 0002_security_controls
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_curriculum_library"
down_revision = "0002_security_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "educational_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(2)),
        sa.Column("system_type", sa.String(80)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "curricula",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("educational_system_id", sa.Integer(), sa.ForeignKey("educational_systems.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("academic_level", sa.String(120)),
        sa.Column("grade_track", sa.String(160)),
        sa.Column("primary_language", sa.String(35), nullable=False, server_default="en"),
        sa.Column("supported_languages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provenance", sa.Text()),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_curricula_educational_system_id", "curricula", ["educational_system_id"])
    op.create_index("ix_curricula_publication_status", "curricula", ["publication_status"])
    op.create_table(
        "curriculum_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("curriculum_id", sa.Integer(), sa.ForeignKey("curricula.id"), nullable=False),
        sa.Column("academic_year", sa.String(40), nullable=False),
        sa.Column("edition", sa.String(80), nullable=False, server_default="1"),
        sa.Column("title", sa.String(255)),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("rights_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("curriculum_id", "academic_year", "edition", name="uq_curriculum_version"),
    )
    op.create_index("ix_curriculum_versions_curriculum_id", "curriculum_versions", ["curriculum_id"])
    op.create_index("ix_curriculum_versions_publication_status", "curriculum_versions", ["publication_status"])

    with op.batch_alter_table("subject_packages") as batch:
        batch.add_column(sa.Column("curriculum_version_id", sa.Integer()))
        batch.add_column(sa.Column("code", sa.String(80)))
        batch.add_column(sa.Column("description", sa.Text()))
        batch.add_column(sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("publication_status", sa.String(20), nullable=False, server_default="published"))
        batch.create_foreign_key("fk_subject_curriculum_version", "curriculum_versions", ["curriculum_version_id"], ["id"])
        batch.create_index("ix_subject_packages_curriculum_version_id", ["curriculum_version_id"])
        batch.create_index("ix_subject_packages_publication_status", ["publication_status"])

    op.create_table(
        "learning_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("resource_type", sa.String(40), nullable=False, server_default="textbook"),
        sa.Column("content_language", sa.String(35), nullable=False, server_default="en"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("rights_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provenance", sa.Text()),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="upload"),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("processing_job_id", sa.String(36), nullable=False),
        sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(60)),
        sa.Column("error_note", sa.String(500)),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("subject_package_id", "sha256", name="uq_subject_resource_checksum"),
    )
    for column in ("subject_package_id", "publication_status", "sha256", "processing_status", "processing_job_id", "uploaded_by_user_id"):
        op.create_index(f"ix_learning_resources_{column}", "learning_resources", [column], unique=column == "processing_job_id")

    op.create_table(
        "curriculum_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("learning_resource_id", sa.Integer(), sa.ForeignKey("learning_resources.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("learning_resource_id", "order_index", name="uq_resource_unit_order"),
    )
    op.create_index("ix_curriculum_units_subject_package_id", "curriculum_units", ["subject_package_id"])
    op.create_index("ix_curriculum_units_learning_resource_id", "curriculum_units", ["learning_resource_id"])

    with op.batch_alter_table("chapters") as batch:
        batch.add_column(sa.Column("learning_resource_id", sa.Integer()))
        batch.add_column(sa.Column("unit_id", sa.Integer()))
        batch.create_foreign_key("fk_chapter_learning_resource", "learning_resources", ["learning_resource_id"], ["id"])
        batch.create_foreign_key("fk_chapter_curriculum_unit", "curriculum_units", ["unit_id"], ["id"])
        batch.create_index("ix_chapters_learning_resource_id", ["learning_resource_id"])
        batch.create_index("ix_chapters_unit_id", ["unit_id"])

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_package_id", sa.Integer(), sa.ForeignKey("subject_packages.id"), nullable=False),
        sa.Column("learning_resource_id", sa.Integer(), sa.ForeignKey("learning_resources.id"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("curriculum_units.id")),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("content_language", sa.String(35), nullable=False, server_default="en"),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("content_text", sa.Text()),
        sa.Column("examples_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("exercises_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("publication_status", sa.String(20), nullable=False, server_default="review"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("learning_resource_id", "order_index", name="uq_resource_lesson_order"),
    )
    for column in ("subject_package_id", "learning_resource_id", "unit_id", "chapter_id", "publication_status"):
        op.create_index(f"ix_lessons_{column}", "lessons", [column])

    with op.batch_alter_table("concepts") as batch:
        batch.add_column(sa.Column("chapter_id", sa.Integer()))
        batch.add_column(sa.Column("lesson_id", sa.Integer()))
        batch.add_column(sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))
        batch.create_foreign_key("fk_concept_chapter", "chapters", ["chapter_id"], ["id"])
        batch.create_foreign_key("fk_concept_lesson", "lessons", ["lesson_id"], ["id"])
        batch.create_index("ix_concepts_chapter_id", ["chapter_id"])
        batch.create_index("ix_concepts_lesson_id", ["lesson_id"])

    with op.batch_alter_table("user_subject_access") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_unique_constraint("uq_user_subject_access", ["user_id", "subject_package_id"])

    op.create_table(
        "user_lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),
    )
    op.create_index("ix_user_lesson_progress_user_id", "user_lesson_progress", ["user_id"])
    op.create_index("ix_user_lesson_progress_lesson_id", "user_lesson_progress", ["lesson_id"])


def downgrade() -> None:
    op.drop_table("user_lesson_progress")
    with op.batch_alter_table("user_subject_access") as batch:
        batch.drop_constraint("uq_user_subject_access", type_="unique")
        batch.drop_column("is_active")
    with op.batch_alter_table("concepts") as batch:
        batch.drop_index("ix_concepts_lesson_id")
        batch.drop_index("ix_concepts_chapter_id")
        batch.drop_constraint("fk_concept_lesson", type_="foreignkey")
        batch.drop_constraint("fk_concept_chapter", type_="foreignkey")
        batch.drop_column("order_index")
        batch.drop_column("lesson_id")
        batch.drop_column("chapter_id")
    op.drop_table("lessons")
    with op.batch_alter_table("chapters") as batch:
        batch.drop_index("ix_chapters_unit_id")
        batch.drop_index("ix_chapters_learning_resource_id")
        batch.drop_constraint("fk_chapter_curriculum_unit", type_="foreignkey")
        batch.drop_constraint("fk_chapter_learning_resource", type_="foreignkey")
        batch.drop_column("unit_id")
        batch.drop_column("learning_resource_id")
    op.drop_table("curriculum_units")
    op.drop_table("learning_resources")
    with op.batch_alter_table("subject_packages") as batch:
        batch.drop_index("ix_subject_packages_publication_status")
        batch.drop_index("ix_subject_packages_curriculum_version_id")
        batch.drop_constraint("fk_subject_curriculum_version", type_="foreignkey")
        batch.drop_column("publication_status")
        batch.drop_column("order_index")
        batch.drop_column("description")
        batch.drop_column("code")
        batch.drop_column("curriculum_version_id")
    op.drop_table("curriculum_versions")
    op.drop_table("curricula")
    op.drop_table("educational_systems")
