"""
Vector store helpers (pgvector) — includes scoped search restricted to a
specific chapter/subject, so RAG answers stay within the current material.
"""
from sqlalchemy.orm import Session

from app.models.embedding import Embedding


def add_embedding(db: Session, content: str, vector: list[float],
                  user_id: int | None = None, meta: dict | None = None,
                  source_ref: str | None = None,
                  subject_package_id: int | None = None,
                  chapter_id: int | None = None,
                  document_id: int | None = None) -> Embedding:
    """Insert one embedding with its scope columns set in the SAME insert —
    no follow-up re-query (the old last()-based update was fragile under
    concurrent workers and could stamp the wrong row)."""
    row = Embedding(content=content, embedding=vector, user_id=user_id,
                    meta=meta or {}, source_ref=source_ref,
                    subject_package_id=subject_package_id,
                    chapter_id=chapter_id,
                    document_id=document_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def search(db: Session, query_vector: list[float], k: int = 5,
           user_id: int | None = None) -> list[dict]:
    """بحث عام (بلا تقييد) — محفوظ للاستخدامات العامة المستقبلية."""
    q = db.query(
        Embedding,
        Embedding.embedding.cosine_distance(query_vector).label("distance"),
    )
    if user_id is not None:
        q = q.filter(Embedding.user_id == user_id)
    rows = q.order_by("distance").limit(k).all()
    return [
        {"id": e.id, "content": e.content, "meta": e.meta,
         "source_ref": e.source_ref, "distance": float(dist)}
        for (e, dist) in rows
    ]


def search_scoped(db: Session, query_vector: list[float], subject_package_id: int,
                   chapter_id: int | None = None, k: int = 5) -> list[dict]:
    """
    بحث مقيّد — الأساس الفعلي لدقة RAG: يبحث فقط بمحتوى المادة، وإذا
    تحدد الفصل، يقيّد البحث بذلك الفصل حصراً.
    """
    q = db.query(
        Embedding,
        Embedding.embedding.cosine_distance(query_vector).label("distance"),
    ).filter(Embedding.subject_package_id == subject_package_id)

    if chapter_id is not None:
        q = q.filter(Embedding.chapter_id == chapter_id)

    rows = q.order_by("distance").limit(k).all()
    return [
        {"id": e.id, "content": e.content, "source_ref": e.source_ref, "distance": float(dist)}
        for (e, dist) in rows
    ]
