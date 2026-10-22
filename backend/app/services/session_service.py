from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.security import RefreshSession


class InvalidRefreshSession(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= _now()


def issue(db: Session, user_id: int, family_id: str | None = None) -> tuple[str, RefreshSession]:
    raw = secrets.token_urlsafe(48)
    row = RefreshSession(
        id=str(uuid.uuid4()),
        family_id=family_id or str(uuid.uuid4()),
        user_id=user_id,
        token_hash=_hash(raw),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(row)
    db.flush()
    return raw, row


def rotate(db: Session, raw: str) -> tuple[int, str]:
    row = db.query(RefreshSession).filter(
        RefreshSession.token_hash == _hash(raw)
    ).with_for_update().first()
    if not row or _expired(row.expires_at):
        raise InvalidRefreshSession()
    if row.revoked_at is not None:
        row.reuse_detected_at = _now()
        revoke_family(db, row.family_id)
        db.commit()
        raise InvalidRefreshSession()
    row.revoked_at = _now()
    new_raw, replacement = issue(db, row.user_id, row.family_id)
    row.replaced_by_id = replacement.id
    db.commit()
    return row.user_id, new_raw


def revoke_token(db: Session, raw: str | None) -> None:
    if not raw:
        return
    row = db.query(RefreshSession).filter(RefreshSession.token_hash == _hash(raw)).first()
    if row and row.revoked_at is None:
        row.revoked_at = _now()
        db.commit()


def revoke_family(db: Session, family_id: str) -> None:
    db.query(RefreshSession).filter(
        RefreshSession.family_id == family_id,
        RefreshSession.revoked_at.is_(None),
    ).update({RefreshSession.revoked_at: _now()}, synchronize_session=False)


def revoke_user(db: Session, user_id: int) -> None:
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked_at.is_(None),
    ).update({RefreshSession.revoked_at: _now()}, synchronize_session=False)
    db.commit()
