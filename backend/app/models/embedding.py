"""
Embeddings table (pgvector) — extended with scoping columns so RAG search can
be restricted to a specific chapter/subject, not just a global search.
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.config import settings
from app.database import Base

if settings.DATABASE_URL.startswith("sqlite"):
    EmbeddingVector = JSON
else:
    from pgvector.sqlalchemy import Vector
    EmbeddingVector = Vector(settings.EMBEDDING_DIM)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # ── أعمدة السياق — تسمح ببحث مقيّد بالفصل/المادة، لا بحث عام ──
    subject_package_id: Mapped[int | None] = mapped_column(ForeignKey("subject_packages.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_documents.id"), index=True)

    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    source_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
