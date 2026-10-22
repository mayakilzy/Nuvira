"""
Vector store helpers (pgvector) — includes scoped search restricted to a
specific chapter/subject, so RAG answers stay within the current material.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

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


def search(db: Session, query_vector: list[float], subject_package_id: int,
           user_id: int, chapter_id: int | None = None, k: int = 5) -> list[dict]:
    """Compatibility entry point with the same mandatory scope as RAG."""
    if not user_id or not subject_package_id:
        raise ValueError("Authenticated user and subject scope are required")
    q = db.query(
        Embedding,
        Embedding.embedding.cosine_distance(query_vector).label("distance"),
    )
    q = q.filter(
        Embedding.subject_package_id == subject_package_id,
        or_(Embedding.user_id.is_(None), Embedding.user_id == user_id),
    )
    if chapter_id is not None:
        q = q.filter(Embedding.chapter_id == chapter_id)
    rows = q.order_by("distance").limit(k).all()
    return [
        {"id": e.id, "content": e.content, "meta": e.meta,
         "source_ref": e.source_ref, "distance": float(dist)}
        for (e, dist) in rows
    ]


def visible_scope_query(db: Session, user_id: int, subject_package_id: int,
                        chapter_id: int | None = None) -> Query:
    """Return only platform-owned rows or private rows owned by this user."""
    if not user_id:
        raise ValueError("Authenticated user_id is required for scoped retrieval")
    query = db.query(Embedding).filter(
        Embedding.subject_package_id == subject_package_id,
        or_(Embedding.user_id.is_(None), Embedding.user_id == user_id),
    )
    if chapter_id is not None:
        query = query.filter(Embedding.chapter_id == chapter_id)
    return query


def search_scoped(db: Session, query_vector: list[float], subject_package_id: int,
                   user_id: int, chapter_id: int | None = None, k: int = 5) -> list[dict]:
    """
    بحث مقيّد — الأساس الفعلي لدقة RAG: يبحث فقط بمحتوى المادة، وإذا
    تحدد الفصل، يقيّد البحث بذلك الفصل حصراً.
    """
    distance = Embedding.embedding.cosine_distance(query_vector).label("distance")
    q = visible_scope_query(db, user_id, subject_package_id, chapter_id).with_entities(
        Embedding, distance
    )

    rows = q.order_by("distance").limit(k).all()
    return [
        {"id": e.id, "content": e.content, "source_ref": e.source_ref, "distance": float(dist)}
        for (e, dist) in rows
    ]
