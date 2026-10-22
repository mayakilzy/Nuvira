"""Paddle Billing (Merchant of Record)."""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.plans import Plan
from app.models.user import User
from app.models.commerce import CreditPack
from app.services.payments.base import CheckoutResult, PaymentProvider, WebhookEvent


def _api_base() -> str:
    return "https://sandbox-api.paddle.com" if settings.PADDLE_ENV != "production" else "https://api.paddle.com"


class PaddleProvider(PaymentProvider):
    name = "paddle"

    async def _create_txn(self, price_id: str, user: User, custom: dict) -> CheckoutResult:
        body = {
            "items": [{"price_id": price_id, "quantity": 1}],
            "custom_data": custom,
            "customer": {"email": user.email},
        }
        headers = {"Authorization": f"Bearer {settings.PADDLE_API_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{_api_base()}/transactions", json=body, headers=headers)
        if r.status_code >= 300:
            raise RuntimeError(f"Paddle txn failed {r.status_code}: {r.text[:300]}")
        data = r.json().get("data", {})
        url = (data.get("checkout") or {}).get("url")
        if not url:
            raise RuntimeError("Paddle did not return a checkout url (set a default payment link in Paddle)")
        return CheckoutResult(url=url)

    async def create_checkout(self, db: Session, user: User, plan: Plan, interval: str = "monthly") -> CheckoutResult:
        price_id = plan.price_id_for("paddle", interval)
        if not price_id:
            raise RuntimeError(f"No paddle price id on plan '{plan.slug}' for {interval}")
        return await self._create_txn(price_id, user, {"user_id": str(user.id), "plan": plan.slug})

    async def create_credit_checkout(self, db: Session, user: User, pack: CreditPack) -> CheckoutResult:
        return await self._create_txn(
            pack.provider_price_id, user, {"user_id": str(user.id), "pack_slug": pack.slug}
        )

    async def create_portal(self, db: Session, user: User) -> CheckoutResult:
        # Paddle Billing manages via API/links; expose a management URL per your setup.
        raise RuntimeError("Configure a Paddle customer management URL for your account")

    def verify_and_parse(self, payload: bytes, headers: dict) -> WebhookEvent:
        # Header: "ts=...;h1=<hmac sha256 of '<ts>:<rawbody>'>"
        raw_sig = headers.get("paddle-signature", "")
        parts = dict(p.split("=", 1) for p in raw_sig.split(";") if "=" in p)
        ts, h1 = parts.get("ts"), parts.get("h1")
        if not ts or not h1:
            raise ValueError("Malformed Paddle-Signature header")
        signed = f"{ts}:".encode() + payload
        digest = hmac.new(settings.PADDLE_WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, h1):
            raise ValueError("Invalid Paddle signature")

        body = json.loads(payload)
        etype = body.get("event_type", "")
        data = body.get("data", {})
        custom = data.get("custom_data") or {}
        user_id = int(custom["user_id"]) if custom.get("user_id") else None

        ev = WebhookEvent(type="ignored", user_id=user_id, raw_type=etype, provider=self.name,
                          provider_subscription_id=data.get("id"))
        if etype in ("subscription.activated", "subscription.updated", "transaction.completed") and not custom.get("pack_slug"):
            ev.type = "subscription_active"
            ev.status = "active"
            ev.plan_slug = custom.get("plan")
            ev.reference_id = str(data.get("id"))
        elif etype in ("subscription.canceled", "subscription.paused"):
            ev.type = "subscription_cancelled"
        elif etype == "transaction.completed" and custom.get("pack_slug"):
            ev.type = "credits_purchased"
            ev.pack_slug = custom["pack_slug"]
            ev.reference_id = str(data.get("id"))
        return ev
