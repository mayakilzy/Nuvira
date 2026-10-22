from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.commerce import PaymentEvent
from app.models.content import UploadedDocument
from app.models.credits import CreditLedger
from app.models.embedding import Embedding
from app.models.preferences import UserApiKey, UserPreferences
from app.models.security import AccountDeletionRequest, OAuthExchange, RefreshSession
from app.models.study import AvatarState, FunFactShownLog, PhraseUsage, StudyLog
from app.models.subject import UserSubjectAccess
from app.models.subscription import Subscription
from app.models.user import User


def cleanup_account(db: Session, request_id: str) -> bool:
    request = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.id == request_id).first()
    if not request or request.status == "completed":
        return True
    request.attempts = (request.attempts or 0) + 1
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        request.status = "completed"
        request.completed_at = datetime.now(timezone.utc)
        db.commit()
        return True
    documents = db.query(UploadedDocument).filter(UploadedDocument.uploaded_by_user_id == user.id).all()
    try:
        for document in documents:
            if document.storage_path and os.path.exists(document.storage_path):
                os.remove(document.storage_path)
    except OSError:
        logging.exception("Account file cleanup failed", extra={"deletion_request_id": request_id})
        request.status = "failed"
        request.error_code = "FILE_DELETE_FAILED"
        db.commit()
        return False

    document_ids = [document.id for document in documents]
    try:
        if document_ids:
            db.query(Embedding).filter(Embedding.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(Embedding).filter(Embedding.user_id == user.id).delete(synchronize_session=False)
        for model in (
            StudyLog, FunFactShownLog, AvatarState, PhraseUsage, UserPreferences,
            UserApiKey, UserSubjectAccess, CreditLedger, Subscription, OAuthExchange,
            RefreshSession, UploadedDocument,
        ):
            field = model.uploaded_by_user_id if model is UploadedDocument else model.user_id
            db.query(model).filter(field == user.id).delete(synchronize_session=False)
        db.query(PaymentEvent).filter(PaymentEvent.user_id == user.id).update(
            {PaymentEvent.user_id: None}, synchronize_session=False
        )
        db.query(AuditLog).filter(AuditLog.user_id == user.id).update({
            AuditLog.user_id: None, AuditLog.old_value: None,
            AuditLog.new_value: None, AuditLog.ip_address: None,
        }, synchronize_session=False)
        db.delete(user)
        request.status = "completed"
        request.error_code = None
        request.completed_at = datetime.now(timezone.utc)
        db.commit()
        return True
    except Exception:
        db.rollback()
        request = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.id == request_id).first()
        request.status = "failed"
        request.error_code = "DATABASE_DELETE_FAILED"
        db.commit()
        logging.exception("Account database cleanup failed", extra={"deletion_request_id": request_id})
        return False
