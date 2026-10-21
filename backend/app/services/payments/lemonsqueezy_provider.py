"""Lemon Squeezy (Merchant of Record) — default provider."""
from __future__ import annotations

import hashlib
import hmac

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.plans import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.payments.base import CheckoutResult, PaymentProvider, WebhookEvent

API = "https://api.lemonsqueezy.com/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.LEMONSQUEEZY_API_KEY}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


class LemonSqueezyProvider(PaymentProvider):
    name = "lemonsqueezy"

    async def _create_checkout(self, variant_id: str, user: User, custom: dict) -> CheckoutResult:
        body = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": user.email,
                        "custom": custom,  # echoed back in webhook meta.custom_data
                    },
                    "product_options": {"redirect_url": f"{settings.FRONTEND_URL}/billing?status=success"},
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": str(settings.LEMONSQUEEZY_STORE_ID)}},
                    "variant": {"data": {"type": "variants", "id": str(variant_id)}},
                },
            }
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{API}/checkouts", json=body, headers=_headers())
        if r.status_code >= 300:
            raise RuntimeError(f"LemonSqueezy checkout failed {r.status_code}: {r.text[:300]}")
        return CheckoutResult(url=r.json()["data"]["attributes"]["url"])

    async def create_checkout(self, db: Session, user: User, plan: Plan, interval: str = "monthly") -> CheckoutResult:
        variant_id = plan.price_id_for("lemonsqueezy", interval)
        if not variant_id:
            raise RuntimeError(f"No lemonsqueezy variant id on plan '{plan.slug}' for {interval}")
        return await self._create_checkout(variant_id, user, {"user_id": str(user.id), "plan": plan.slug})

    async def create_credit_checkout(self, db: Session, user: User, price_id: str, credits: int) -> CheckoutResult:
        return await self._create_checkout(price_id, user, {"user_id": str(user.id), "credits": str(credits)})

    async def create_portal(self, db: Session, user: User) -> CheckoutResult:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if not sub or not sub.stripe_subscription_id:
            raise RuntimeError("No subscription to manage")
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{API}/subscriptions/{sub.stripe_subscription_id}", headers=_headers())
        urls = r.json().get("data", {}).get("attributes", {}).get("urls", {})
        portal = urls.get("customer_portal")
        if not portal:
            raise RuntimeError("Customer portal not available")
        return CheckoutResult(url=portal)

    def verify_and_parse(self, payload: bytes, headers: dict) -> WebhookEvent:
        secret = settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode()
        signature = headers.get("x-signature", "")
        digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, signature):
            raise ValueError("Invalid Lemon Squeezy signature")

        import json
        body = json.loads(payload)
        meta = body.get("meta", {})
        event_name = meta.get("event_name", "")
        custom = meta.get("custom_data", {}) or {}
        attrs = body.get("data", {}).get("attributes", {})
        sub_id = body.get("data", {}).get("id")
        user_id = int(custom["user_id"]) if custom.get("user_id") else None

        ev = WebhookEvent(type="ignored", user_id=user_id, raw_type=event_name,
                          provider_subscription_id=sub_id)

        if event_name in ("subscription_created", "subscription_updated", "subscription_payment_success"):
            ev.type = "subscription_active"
            ev.status = "active"
            ev.plan_slug = custom.get("plan")
            ev.reference_id = str(attrs.get("renews_at") or sub_id)
        elif event_name in ("subscription_cancelled", "subscription_expired"):
            ev.type = "subscription_cancelled"
        elif event_name == "order_created" and custom.get("credits"):
            ev.type = "credits_purchased"
            ev.credits = int(custom["credits"])
            ev.reference_id = str(body.get("data", {}).get("id"))
        return ev
