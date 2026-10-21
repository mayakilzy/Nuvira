from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.tokens import create_reset_token, create_verify_token, read_token
from app.database import get_db
from app.models.user import User
from app.services import email_service, oauth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def normalize_email(email: str) -> str:
    """Emails are case-insensitive: strip whitespace and lowercase before
    storing or looking up, so 'Sweet@x.com' and 'sweet@x.com' are the same account."""
    return email.strip().lower()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _tokens(user_id: int) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(str(user_id)),
        refresh_token=create_refresh_token(str(user_id)),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    await email_service.send_verification_email(user.email, create_verify_token(str(user.id)))
    return _tokens(user.id)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    return _tokens(user.id)


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    return _tokens(int(payload["sub"]))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "is_verified": user.is_verified, "avatar_url": user.avatar_url}


@router.post("/logout")
def logout():
    return {"detail": "ok"}


# ---------- Email verification ----------
@router.get("/verify-email/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    uid = read_token(token, "verify_email")
    if not uid:
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).filter(User.id == int(uid)).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_verified = True
    db.commit()
    return {"detail": "Email verified"}


# ---------- Password reset ----------
class ForgotIn(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
async def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    user = db.query(User).filter(User.email == email).first()
    # Always return ok (don't leak which emails exist)
    if user:
        await email_service.send_reset_email(user.email, create_reset_token(str(user.id)))
    return {"detail": "If the email exists, a reset link was sent"}


class ResetIn(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    uid = read_token(data.token, "reset_password")
    if not uid:
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).filter(User.id == int(uid)).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"detail": "Password updated"}


# ---------- Google OAuth ----------
@router.get("/google")
def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(501, "Google OAuth not configured")
    return RedirectResponse(oauth_service.build_consent_url())


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    profile = await oauth_service.exchange_code(code)
    if not profile.get("email"):
        raise HTTPException(400, "Google did not return an email")
    email = normalize_email(profile["email"])
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=profile.get("name"),
                    avatar_url=profile.get("picture"), google_id=profile.get("sub"),
                    is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.google_id:
        user.google_id = profile.get("sub")
        user.is_verified = True
        db.commit()
    t = _tokens(user.id)
    # hand tokens to the frontend
    return RedirectResponse(f"{settings.FRONTEND_URL}/login?access_token={t.access_token}&refresh_token={t.refresh_token}")
