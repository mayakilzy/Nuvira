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
from app.services.payments import fulfill, get_provider

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """Public: active plans for pricing pages (no secrets exposed)."""
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
    plan = db.query(Plan).filter(Plan.slug == data.plan_slug, Plan.is_active == True).first()  # noqa: E712
    if not plan:
        raise HTTPException(404, "Plan not found")
    try:
        res = await get_provider().create_checkout(db, user, plan, data.interval)
    except Exception as e:
        raise HTTPException(502, f"Checkout error: {e}")
    return {"url": res.url}


class CreditPackIn(BaseModel):
    price_id: str      # provider variant/price id for the credit pack
    credits: int


@router.post("/buy-credits")
async def buy_credits(data: CreditPackIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    try:
        res = await get_provider().create_credit_checkout(db, user, data.price_id, data.credits)
    except Exception as e:
        raise HTTPException(502, f"Checkout error: {e}")
    return {"url": res.url}


@router.post("/create-portal-session")
async def create_portal(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        res = await get_provider().create_portal(db, user)
    except Exception as e:
        raise HTTPException(502, f"Portal error: {e}")
    return {"url": res.url}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
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
