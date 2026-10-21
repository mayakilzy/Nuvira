from sqlalchemy import String, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    price_monthly: Mapped[int] = mapped_column(Integer, default=0)  # in cents
    price_yearly: Mapped[int] = mapped_column(Integer, default=0)

    stripe_price_id_monthly: Mapped[str | None] = mapped_column(String(255))
    stripe_price_id_yearly: Mapped[str | None] = mapped_column(String(255))

    # Generic per-provider price/variant ids, e.g.
    # {"lemonsqueezy": {"monthly": "123", "yearly": "124"},
    #  "paddle": {"monthly": "pri_x"}, "stripe": {"monthly": "price_x"}}
    provider_price_ids: Mapped[dict] = mapped_column(JSON, default=dict)

    credits_per_month: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def price_id_for(self, provider: str, interval: str = "monthly") -> str | None:
        """Resolve the price/variant id for a provider + interval."""
        ids = (self.provider_price_ids or {}).get(provider, {})
        if ids.get(interval):
            return ids[interval]
        # backward-compat fallback for stripe's dedicated columns
        if provider == "stripe":
            return self.stripe_price_id_yearly if interval == "yearly" else self.stripe_price_id_monthly
        return None
