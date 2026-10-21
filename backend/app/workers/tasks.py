"""
=============================================================================
 BACKGROUND TASKS  —  PER PROJECT.  Add Celery tasks for your product here.
=============================================================================
"""
import asyncio

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services import document_service


@celery_app.task
def ping() -> str:
    """Health task so you can verify the worker end-to-end."""
    return "pong"


@celery_app.task(name="process_uploaded_document")
def process_uploaded_document_task(document_id: int):
    """
    يُستدعى بعد كل رفع ملف — يستخرج النص، يقطّعه، يحوّله لـ embeddings
    مقيّدة بالفصل/المادة، ويحدّث حالة الملف (ready/failed).
    """
    db = SessionLocal()
    try:
        asyncio.run(document_service.process_document(db, document_id))
    finally:
        db.close()
