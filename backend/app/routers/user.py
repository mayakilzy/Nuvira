"""User profile, password change, and verifiable account deletion."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.models.security import AccountDeletionRequest
from app.services import account_deletion_service, session_service

router = APIRouter(prefix="/user", tags=["user"])


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "avatar_url": user.avatar_url, "role": user.role}


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    db.commit()
    return {"detail": "updated"}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 12 or not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must be at least 12 characters and include letters and numbers")
        return value


@router.put("/password")
def change_password(data: PasswordChange, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not user.password_hash or not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    session_service.revoke_user(db, user.id)
    db.commit()
    return {"detail": "password updated"}


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.is_active = False
    session_service.revoke_user(db, user.id)
    request = AccountDeletionRequest(id=str(uuid.uuid4()), user_id=user.id, status="pending")
    db.add(request)
    db.commit()
    if account_deletion_service.cleanup_account(db, request.id):
        return {"detail": "account deleted", "deletion_request_id": request.id}
    from app.workers.tasks import retry_account_deletion_task
    try:
        retry_account_deletion_task.delay(request.id)
    except Exception:
        raise HTTPException(
            503,
            detail={
                "code": "DELETION_RETRY_UNAVAILABLE",
                "message": "Account is disabled and deletion cleanup is pending",
                "deletion_request_id": request.id,
            },
        )
    return {"detail": "account disabled; deletion cleanup queued", "deletion_request_id": request.id}
