"""User profile, password change, and account deletion."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models.user import User

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


@router.put("/password")
def change_password(data: PasswordChange, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not user.password_hash or not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"detail": "password updated"}


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"detail": "account deleted"}
