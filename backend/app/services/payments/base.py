"""
Provider-agnostic billing core.

- `PaymentProvider` is the interface every gateway implements.
- `WebhookEvent` is the NORMALIZED event all providers map their raw events to,
  so the rest of the app never sees provider-specific shapes.
- `fulfill()` is the single, shared place that activates subscriptions and grants
  credits. It is idempotent (safe against webhook retries / duplicates).

Adding a new gateway = one adapter file + one line in the factory. Nothing here
or in the router changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.credits import CreditLedger
from app.models.plans import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.models.commerce import CreditPack, PaymentEvent


@dataclass
class CheckoutResult:
    url: str


@dataclass
class WebhookEvent:
    """Normalized event. `type` is one of:
    subscription_active | subscription_cancelled | credits_purchased | ignored
    """
    type: str
    user_id: int | None = None
    plan_slug: str | None = None
    status: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    credits: int = 0
    provider: str = "unknown"
    pack_slug: str | None = None
    reference_id: str | None = None          # invoice/period/order id (idempotency key)
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    raw_type: str | None = None
    extra: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def create_checkout(self, db: Session, user: User, plan: Plan, interval: str = "monthly") -> CheckoutResult:
        ...

    @abstractmethod
    async def create_credit_checkout(self, db: Session, user: User, pack: CreditPack) -> CheckoutResult:
        ...

    @abstractmethod
    async def create_portal(self, db: Session, user: User) -> CheckoutResult:
        ...

    @abstractmethod
    def verify_and_parse(self, payload: bytes, headers: dict) -> WebhookEvent:
        """Verify the signature (raise on failure) and return a normalized event."""
        ...


# --------------------------------------------------------------------------
#  Shared, idempotent fulfillment — used by every provider's webhook.
# --------------------------------------------------------------------------
def _already_granted(db: Session, reference_id: str | None, types: tuple[str, ...]) -> bool:
    if not reference_id:
        return False
    return (
        db.query(CreditLedger)
        .filter(CreditLedger.reference_id == reference_id, CreditLedger.type.in_(types))
        .first()
        is not None
    )


def _grant(db: Session, user_id: int, amount: int, type_: str, description: str, reference_id: str | None):
    """Append a credit grant unless this reference was already granted."""
    if amount <= 0:
        return
    if _already_granted(db, reference_id, (type_,)):
        return  # idempotent: webhook retry / duplicate
    balance_after = (
        db.query(CreditLedger).with_entities(CreditLedger.amount).filter(CreditLedger.user_id == user_id).all()
    )
    current = sum(a for (a,) in balance_after)
    db.add(CreditLedger(
        user_id=user_id, amount=amount, type=type_,
        description=description, reference_id=reference_id, balance_after=current + amount,
    ))


def _upsert_subscription(db: Session, ev: WebhookEvent):
    sub = db.query(Subscription).filter(Subscription.user_id == ev.user_id).first()
    if not sub:
        sub = Subscription(user_id=ev.user_id)
        db.add(sub)
    if ev.plan_slug:
        sub.plan = ev.plan_slug
    if ev.status:
        sub.status = ev.status
    if ev.period_start:
        sub.current_period_start = ev.period_start
    if ev.period_end:
        sub.current_period_end = ev.period_end
    if ev.provider_customer_id:
        sub.stripe_customer_id = ev.provider_customer_id        # generic: provider customer id
    if ev.provider_subscription_id:
        sub.stripe_subscription_id = ev.provider_subscription_id  # generic: provider sub id
    return sub


def fulfill(db: Session, ev: WebhookEvent) -> None:
    if ev.type == "ignored" or ev.user_id is None:
        return

    if not ev.reference_id:
        return
    db.add(PaymentEvent(
        provider=ev.provider,
        event_id=ev.reference_id,
        event_type=ev.type,
        user_id=ev.user_id,
    ))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return

    if ev.type == "subscription_active":
        ev.status = ev.status or "active"
        _upsert_subscription(db, ev)
        # grant the plan's monthly credits (once per billing period via reference_id)
        plan = db.query(Plan).filter(Plan.slug == ev.plan_slug).first() if ev.plan_slug else None
        # Never fall back to a quantity supplied by provider metadata. Credits
        # are granted only from a server-owned, active plan definition.
        credits = plan.credits_per_month if plan and plan.is_active else 0
        _grant(db, ev.user_id, credits, "subscription_grant",
               f"plan:{ev.plan_slug}", ev.reference_id)

    elif ev.type == "subscription_cancelled":
        ev.status = "cancelled"
        _upsert_subscription(db, ev)

    elif ev.type == "credits_purchased":
        pack = db.query(CreditPack).filter(
            CreditPack.slug == ev.pack_slug,
            CreditPack.provider == ev.provider,
            CreditPack.is_active.is_(True),
        ).first()
        if not pack:
            db.rollback()
            return
        _grant(db, ev.user_id, pack.credits, "purchase",
               f"credit-pack:{pack.slug}", ev.reference_id)

    db.commit()
