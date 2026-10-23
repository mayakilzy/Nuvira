"""
Chapters + uploaded materials — تنظيم المنهج حسب فصول الكتاب، وتتبع كل ملف
مرفوع وحالة معالجته (استخراج نص -> تقطيع -> embeddings).
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Chapter(Base):
    """فصل واحد من فصول الكتاب/المنهج (مثال: الفصل 4 من 12)."""
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    learning_resource_id: Mapped[int | None] = mapped_column(ForeignKey("learning_resources.id"), index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("curriculum_units.id"), index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UploadedDocument(Base):
    """سجل كل ملف رفعته الطالبة — للتتبع وإعادة المعالجة لو فشلت."""
    __tablename__ = "uploaded_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    subject_package_id: Mapped[int] = mapped_column(ForeignKey("subject_packages.id"), index=True, nullable=False)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    # processing | ready | failed
    error_note: Mapped[str | None] = mapped_column(String(500))
    error_code: Mapped[str | None] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
