"""
Seed default plans + the first admin. Idempotent: safe to run on every boot.
Edit DEFAULT_PLANS per product (prices, credits, provider variant ids).
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.models.plans import Plan
from app.models.user import User

DEFAULT_PLANS = [
    {"name": "Free", "slug": "free", "price_monthly": 0, "credits_per_month": 50,
     "features": {"support": "community"}},
    {"name": "Starter", "slug": "starter", "price_monthly": 1900, "credits_per_month": 1000,
     "features": {"support": "email"}, "provider_price_ids": {"lemonsqueezy": {"monthly": ""}}},
    {"name": "Pro", "slug": "pro", "price_monthly": 4900, "credits_per_month": 5000,
     "features": {"support": "priority"}, "provider_price_ids": {"lemonsqueezy": {"monthly": ""}}},
]


def seed(db: Session) -> None:
    # plans
    for spec in DEFAULT_PLANS:
        if not db.query(Plan).filter(Plan.slug == spec["slug"]).first():
            db.add(Plan(**spec))
    # first admin (emails are case-insensitive — normalize before lookup)
    email = settings.FIRST_ADMIN_EMAIL.strip().lower() if settings.FIRST_ADMIN_EMAIL else ""
    if email and not db.query(User).filter(User.email == email).first():
        db.add(User(
            email=email,
            password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
            full_name="Admin",
            role="admin",
            is_active=True,
            is_verified=True,
        ))
    db.commit()
