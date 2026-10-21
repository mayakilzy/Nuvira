"""Factory: returns the configured payment provider. Switch via PAYMENT_PROVIDER."""
from functools import lru_cache

from app.config import settings
from app.services.payments.base import PaymentProvider, WebhookEvent, CheckoutResult, fulfill


@lru_cache
def get_provider() -> PaymentProvider:
    name = settings.PAYMENT_PROVIDER.lower()
    if name == "lemonsqueezy":
        from app.services.payments.lemonsqueezy_provider import LemonSqueezyProvider
        return LemonSqueezyProvider()
    if name == "paddle":
        from app.services.payments.paddle_provider import PaddleProvider
        return PaddleProvider()
    if name == "stripe":
        from app.services.payments.stripe_provider import StripeProvider
        return StripeProvider()
    raise ValueError(f"Unknown PAYMENT_PROVIDER: {settings.PAYMENT_PROVIDER}")


__all__ = ["get_provider", "PaymentProvider", "WebhookEvent", "CheckoutResult", "fulfill"]
