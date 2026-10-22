import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.commerce import CreditPack
from app.models.content import UploadedDocument
from app.models.credits import CreditLedger
from app.models.embedding import Embedding
from app.models.security import AccountDeletionRequest, RefreshSession
from app.models.subject import SubjectPackage
from app.models.user import User
from app.routers.agent import _validate_upload_file
from app.services import account_deletion_service, vector_service
from app.services.payments.base import WebhookEvent, fulfill


def _database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _embedding():
    return [0.1] * 1536


def test_rag_returns_platform_and_current_user_but_not_other_student():
    db = _database()
    subject = SubjectPackage(name="Security", language="en")
    db.add(subject); db.flush()
    db.add_all([
        Embedding(user_id=None, subject_package_id=subject.id, content="platform", embedding=_embedding(), meta={}),
        Embedding(user_id=1, subject_package_id=subject.id, content="student-a", embedding=_embedding(), meta={}),
        Embedding(user_id=2, subject_package_id=subject.id, content="student-b", embedding=_embedding(), meta={}),
    ])
    db.commit()
    visible = {row.content for row in vector_service.visible_scope_query(db, 1, subject.id).all()}
    assert visible == {"platform", "student-a"}
    try:
        vector_service.visible_scope_query(db, 0, subject.id)
        assert False, "missing user context must fail closed"
    except ValueError:
        pass
    try:
        vector_service.search(db, _embedding(), subject.id, 0)
        assert False, "generic retrieval must require an authenticated user"
    except ValueError:
        pass


def test_credit_pack_is_server_owned_and_duplicate_event_grants_once():
    db = _database()
    user = User(email="credits@example.com", is_active=True)
    db.add(user); db.flush()
    db.add(CreditPack(slug="approved", provider="stripe", provider_price_id="price_1",
                      credits=100, is_active=True))
    db.commit()
    event = WebhookEvent(type="credits_purchased", user_id=user.id, provider="stripe",
                         pack_slug="approved", credits=999999, reference_id="evt_same")
    fulfill(db, event)
    fulfill(db, event)
    rows = db.query(CreditLedger).filter(CreditLedger.user_id == user.id).all()
    assert len(rows) == 1
    assert rows[0].amount == 100


def test_unknown_subscription_plan_never_uses_event_credit_quantity():
    db = _database()
    user = User(email="subscription@example.com", is_active=True)
    db.add(user); db.commit()
    fulfill(db, WebhookEvent(
        type="subscription_active", user_id=user.id, provider="stripe",
        plan_slug="unknown", credits=999999, reference_id="evt_unknown_plan",
    ))
    assert db.query(CreditLedger).filter(CreditLedger.user_id == user.id).count() == 0


def test_upload_signature_validation_rejects_forged_pdf_and_legacy_ppt(tmp_path):
    forged = tmp_path / "forged.pdf"
    forged.write_bytes(b"not a pdf")
    try:
        _validate_upload_file(str(forged), ".pdf")
        assert False, "forged extension accepted"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    try:
        _validate_upload_file(str(forged), ".ppt")
        assert False, "legacy ppt accepted"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400


def test_account_cleanup_failure_is_detected_then_retry_completes(tmp_path, monkeypatch):
    db = _database()
    user = User(email="delete@example.com", is_active=False)
    db.add(user); db.flush()
    other_user = User(email="keep@example.com", is_active=True)
    db.add(other_user); db.flush()
    file_path = tmp_path / "private.pdf"
    file_path.write_bytes(b"%PDF-private")
    doc = UploadedDocument(uploaded_by_user_id=user.id, subject_package_id=1,
        filename="private.pdf", storage_path=str(file_path), status="ready", file_size=file_path.stat().st_size)
    db.add(doc); db.flush()
    db.add(Embedding(user_id=user.id, document_id=doc.id, content="private", embedding=_embedding(), meta={}))
    db.add(Embedding(user_id=other_user.id, content="other-private", embedding=_embedding(), meta={}))
    db.add(Embedding(user_id=None, content="platform-shared", embedding=_embedding(), meta={}))
    request = AccountDeletionRequest(id="delete-1", user_id=user.id, status="pending")
    db.add(request); db.commit()

    real_remove = os.remove
    monkeypatch.setattr(os, "remove", lambda path: (_ for _ in ()).throw(OSError("locked")))
    assert account_deletion_service.cleanup_account(db, request.id) is False
    db.refresh(request)
    assert request.status == "failed" and request.error_code == "FILE_DELETE_FAILED"
    monkeypatch.setattr(os, "remove", real_remove)
    assert account_deletion_service.cleanup_account(db, request.id) is True
    assert db.query(User).filter(User.id == user.id).first() is None
    assert db.query(Embedding).filter(Embedding.user_id == user.id).count() == 0
    assert db.query(User).filter(User.id == other_user.id).one()
    assert db.query(Embedding).filter(Embedding.user_id == other_user.id).one().content == "other-private"
    assert db.query(Embedding).filter(Embedding.user_id.is_(None)).one().content == "platform-shared"
    assert not file_path.exists()
