"""
Provider-agnostic billing router. Works identically for Lemon Squeezy, Paddle,
and Stripe — the active one is chosen by PAYMENT_PROVIDER in .env.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.plans import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.models.commerce import CreditPack
from app.config import settings
from app.services.payments import fulfill, get_provider

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """Public: active plans for pricing pages (no secrets exposed)."""
    if not settings.PAYMENTS_ENABLED:
        return []
    plans = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_monthly).all()  # noqa: E712
    return [
        {"name": p.name, "slug": p.slug, "price_monthly": p.price_monthly,
         "price_yearly": p.price_yearly, "credits_per_month": p.credits_per_month,
         "features": p.features}
        for p in plans
    ]


class CheckoutIn(BaseModel):
    plan_slug: str
    interval: str = "monthly"


@router.post("/create-checkout-session")
async def create_checkout(data: CheckoutIn, user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(503, "Payments are disabled")
    if data.interval not in ("monthly", "yearly"):
        raise HTTPException(400, "Invalid billing interval")
    plan = db.query(Plan).filter(Plan.slug == data.plan_slug, Plan.is_active == True).first()  # noqa: E712
    if not plan:
        raise HTTPException(404, "Plan not found")
    try:
        res = await get_provider().create_checkout(db, user, plan, data.interval)
    except Exception:
        raise HTTPException(502, "Checkout provider unavailable")
    return {"url": res.url}


class CreditPackIn(BaseModel):
    pack_slug: str


@router.post("/buy-credits")
async def buy_credits(data: CreditPackIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(503, "Credit purchases are disabled")
    pack = db.query(CreditPack).filter(
        CreditPack.slug == data.pack_slug,
        CreditPack.provider == settings.PAYMENT_PROVIDER,
        CreditPack.is_active.is_(True),
    ).first()
    if not pack:
        raise HTTPException(404, "Credit pack not available")
    try:
        res = await get_provider().create_credit_checkout(db, user, pack)
    except Exception:
        raise HTTPException(502, "Checkout provider unavailable")
    return {"url": res.url}


@router.post("/create-portal-session")
async def create_portal(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(503, "Payments are disabled")
    try:
        res = await get_provider().create_portal(db, user)
    except Exception:
        raise HTTPException(502, "Billing portal unavailable")
    return {"url": res.url}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(503, "Payments are disabled")
    payload = await request.body()
    try:
        event = get_provider().verify_and_parse(payload, dict(request.headers))
    except Exception:
        raise HTTPException(400, "Invalid webhook signature")
    fulfill(db, event)
    return {"received": True}


@router.get("/subscription")
def subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        return {"plan": "free", "status": "active"}
    return {
        "plan": sub.plan, "status": sub.status,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }
