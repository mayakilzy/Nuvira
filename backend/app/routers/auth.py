from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.core.tokens import create_reset_token, create_verify_token, read_token
from app.database import get_db
from app.models.user import User
from app.services import email_service, oauth_service, session_service

router = APIRouter(prefix="/auth", tags=["auth"])


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password(value: str) -> str:
    if len(value) < 12 or not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Password must be at least 12 characters and include letters and numbers")
    return value


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    _password_policy = field_validator("password")(_validate_password)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    return_path: str | None = None


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(settings.REFRESH_COOKIE_NAME, token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, httponly=True,
        secure=settings.ENV == "production", samesite="lax", path="/auth")


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/auth", samesite="lax")


def _new_session(db: Session, response: Response, user_id: int, return_path: str | None = None) -> TokenOut:
    raw, _ = session_service.issue(db, user_id)
    db.commit()
    _set_refresh_cookie(response, raw)
    return TokenOut(access_token=create_access_token(str(user_id)), return_path=return_path)


def _check_cookie_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        if settings.ENV == "production":
            raise HTTPException(403, "Origin required")
        return
    allowed = {settings.FRONTEND_URL.rstrip("/")}
    allowed.update(x.strip().rstrip("/") for x in settings.EXTRA_CORS_ORIGINS.split(",") if x.strip())
    if origin.rstrip("/") not in allowed:
        raise HTTPException(403, "Invalid origin")


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    if settings.EMAIL_ENABLED:
        await email_service.send_verification_email(user.email, create_verify_token(str(user.id)))
    return _new_session(db, response, user.id)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == normalize_email(data.email)).first()
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    return _new_session(db, response, user.id)


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    _check_cookie_origin(request)
    raw = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw:
        raise HTTPException(401, "Invalid refresh session")
    try:
        user_id, replacement = session_service.rotate(db, raw)
    except session_service.InvalidRefreshSession:
        _clear_refresh_cookie(response)
        raise HTTPException(401, "Invalid refresh session")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(401, "Invalid refresh session")
    _set_refresh_cookie(response, replacement)
    return TokenOut(access_token=create_access_token(str(user_id)))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "is_verified": user.is_verified, "avatar_url": user.avatar_url}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    _check_cookie_origin(request)
    session_service.revoke_token(db, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    _clear_refresh_cookie(response)
    return {"detail": "ok"}


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


class ForgotIn(BaseModel):
    email: EmailStr


@router.post("/forgot-password")
async def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == normalize_email(data.email)).first()
    if user and settings.EMAIL_ENABLED:
        await email_service.send_reset_email(user.email, create_reset_token(str(user.id)))
    return {"detail": "If the email exists, a reset link was sent"}


class ResetIn(BaseModel):
    token: str
    new_password: str
    _password_policy = field_validator("new_password")(_validate_password)


@router.post("/reset-password")
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    uid = read_token(data.token, "reset_password")
    if not uid:
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).filter(User.id == int(uid)).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.password_hash = hash_password(data.new_password)
    session_service.revoke_user(db, user.id)
    db.commit()
    return {"detail": "Password updated"}


@router.get("/google")
def google_login(return_path: str | None = None, db: Session = Depends(get_db)):
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(503, "Google OAuth is disabled")
    return RedirectResponse(oauth_service.begin(db, return_path))


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(503, "Google OAuth is disabled")
    try:
        state_row = oauth_service.consume_state(db, state)
    except oauth_service.InvalidOAuthState:
        raise HTTPException(400, "Invalid or expired OAuth state")
    try:
        profile = await oauth_service.exchange_code(code, state_row.code_verifier)
    except oauth_service.OAuthProviderError:
        raise HTTPException(400, "OAuth provider authentication failed")
    if not profile.get("sub") or not profile.get("email") or not profile.get("email_verified"):
        raise HTTPException(400, "Google identity is not verified")
    email = normalize_email(profile["email"])
    user = db.query(User).filter(User.google_id == profile["sub"]).first()
    email_user = db.query(User).filter(User.email == email).first()
    if user and user.email != email:
        raise HTTPException(409, "Google identity does not match the account email")
    if not user and email_user:
        raise HTTPException(409, "Sign in with your password before linking Google")
    if not user:
        user = User(email=email, full_name=profile.get("name"), avatar_url=profile.get("picture"),
                    google_id=profile["sub"], is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    exchange = oauth_service.create_exchange(db, user.id, state_row.return_path)
    return RedirectResponse(f"{settings.FRONTEND_URL}/login?{urlencode({'oauth_code': exchange})}", status_code=303)


class OAuthExchangeIn(BaseModel):
    code: str


@router.post("/oauth/exchange", response_model=TokenOut)
def oauth_exchange(data: OAuthExchangeIn, response: Response, db: Session = Depends(get_db)):
    try:
        row = oauth_service.consume_exchange(db, data.code)
    except oauth_service.InvalidOAuthState:
        raise HTTPException(400, "Invalid or expired OAuth exchange")
    return _new_session(db, response, row.user_id, row.return_path)
