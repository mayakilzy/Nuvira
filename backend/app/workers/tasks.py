"""
=============================================================================
 BACKGROUND TASKS  —  PER PROJECT.  Add Celery tasks for your product here.
=============================================================================
"""
import asyncio

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services import document_service
from app.services import account_deletion_service
from app.services import curriculum_processing_service


@celery_app.task
def ping() -> str:
    """Health task so you can verify the worker end-to-end."""
    return "pong"


@celery_app.task(bind=True, name="process_uploaded_document", max_retries=2)
def process_uploaded_document_task(self, document_id: int):
    """
    يُستدعى بعد كل رفع ملف — يستخرج النص، يقطّعه، يحوّله لـ embeddings
    مقيّدة بالفصل/المادة، ويحدّث حالة الملف (ready/failed).
    """
    db = SessionLocal()
    try:
        try:
            asyncio.run(document_service.process_document(db, document_id))
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        db.close()


@celery_app.task(bind=True, name="process_curriculum_resource", max_retries=3)
def process_curriculum_resource_task(self, resource_id: int):
    """Extract a stable draft hierarchy. Replays replace drafts instead of duplicating them."""
    db = SessionLocal()
    try:
        try:
            curriculum_processing_service.process_resource(db, resource_id)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        db.close()


@celery_app.task(bind=True, name="retry_account_deletion", max_retries=3)
def retry_account_deletion_task(self, request_id: str):
    db = SessionLocal()
    try:
        if not account_deletion_service.cleanup_account(db, request_id):
            raise self.retry(countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
