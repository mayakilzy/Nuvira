"""Stripe (payment processor — buyer handles their own tax/VAT)."""
from __future__ import annotations

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models.plans import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.payments.base import CheckoutResult, PaymentProvider, WebhookEvent


class StripeProvider(PaymentProvider):
    name = "stripe"

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_checkout(self, db: Session, user: User, plan: Plan, interval: str = "monthly") -> CheckoutResult:
        price_id = plan.price_id_for("stripe", interval)
        if not price_id:
            raise RuntimeError(f"No stripe price id on plan '{plan.slug}' for {interval}")
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user.email,
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id), "plan": plan.slug},
            success_url=f"{settings.FRONTEND_URL}/billing?status=success",
            cancel_url=f"{settings.FRONTEND_URL}/billing?status=cancel",
        )
        return CheckoutResult(url=session.url)

    async def create_credit_checkout(self, db: Session, user: User, price_id: str, credits: int) -> CheckoutResult:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user.email,
            metadata={"user_id": str(user.id), "credits": str(credits)},
            success_url=f"{settings.FRONTEND_URL}/billing?status=success",
            cancel_url=f"{settings.FRONTEND_URL}/billing?status=cancel",
        )
        return CheckoutResult(url=session.url)

    async def create_portal(self, db: Session, user: User) -> CheckoutResult:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if not sub or not sub.stripe_customer_id:
            raise RuntimeError("No Stripe customer to manage")
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return CheckoutResult(url=session.url)

    def verify_and_parse(self, payload: bytes, headers: dict) -> WebhookEvent:
        sig = headers.get("stripe-signature", "")
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
        etype = event["type"]
        obj = event["data"]["object"]
        meta = obj.get("metadata", {}) or {}
        user_id = int(meta["user_id"]) if meta.get("user_id") else None

        ev = WebhookEvent(type="ignored", user_id=user_id, raw_type=etype)
        if etype == "checkout.session.completed":
            if obj.get("mode") == "payment" and meta.get("credits"):
                ev.type = "credits_purchased"
                ev.credits = int(meta["credits"])
                ev.reference_id = obj.get("id")
            else:
                ev.type = "subscription_active"
                ev.status = "active"
                ev.plan_slug = meta.get("plan")
                ev.provider_customer_id = obj.get("customer")
                ev.provider_subscription_id = obj.get("subscription")
                ev.reference_id = obj.get("id")
        elif etype == "invoice.payment_succeeded":
            ev.type = "subscription_active"
            ev.status = "active"
            ev.provider_customer_id = obj.get("customer")
            ev.reference_id = obj.get("id")  # invoice id -> one grant per period
        elif etype == "customer.subscription.deleted":
            ev.type = "subscription_cancelled"
            ev.provider_customer_id = obj.get("customer")
        return ev
