"""Universal curriculum hierarchy and publication lifecycle."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EducationalSystem(Base):
    __tablename__ = "educational_systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    system_type: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Curriculum(Base):
    __tablename__ = "curricula"

    id: Mapped[int] = mapped_column(primary_key=True)
    educational_system_id: Mapped[int] = mapped_column(
        ForeignKey("educational_systems.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    academic_level: Mapped[str | None] = mapped_column(String(120))
    grade_track: Mapped[str | None] = mapped_column(String(160))
    primary_language: Mapped[str] = mapped_column(String(35), default="en")
    supported_languages: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[str | None] = mapped_column(Text)
    publication_status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CurriculumVersion(Base):
    __tablename__ = "curriculum_versions"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "academic_year", "edition", name="uq_curriculum_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    curriculum_id: Mapped[int] = mapped_column(ForeignKey("curricula.id"), index=True, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(40), nullable=False)
    edition: Mapped[str] = mapped_column(String(80), nullable=False, default="1")
    title: Mapped[str | None] = mapped_column(String(255))
    publication_status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    rights_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningResource(Base):
    __tablename__ = "learning_resources"
    __table_args__ = (
        UniqueConstraint("subject_package_id", "sha256", name="uq_subject_resource_checksum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_package_id: Mapped[int] = mapped_column(
        ForeignKey("subject_packages.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(40), default="textbook")
    content_language: Mapped[str] = mapped_column(String(35), default="en")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    publication_status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    rights_status: Mapped[str] = mapped_column(String(20), default="pending")
    provenance: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(20), default="upload")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    processing_job_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(60))
    error_note: Mapped[str | None] = mapped_column(String(500))
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CurriculumUnit(Base):
    __tablename__ = "curriculum_units"
    __table_args__ = (
        UniqueConstraint("learning_resource_id", "order_index", name="uq_resource_unit_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    learning_resource_id: Mapped[int] = mapped_column(ForeignKey("learning_resources.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("learning_resource_id", "order_index", name="uq_resource_lesson_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    learning_resource_id: Mapped[int] = mapped_column(ForeignKey("learning_resources.id"), index=True, nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("curriculum_units.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    content_language: Mapped[str] = mapped_column(String(35), default="en")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    content_text: Mapped[str | None] = mapped_column(Text)
    examples_json: Mapped[list] = mapped_column(JSON, default=list)
    exercises_json: Mapped[list] = mapped_column(JSON, default=list)
    publication_status: Mapped[str] = mapped_column(String(20), default="review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
