from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CreditLedger(Base):
    """Append-only ledger. Balance = SUM(amount) for a user. Never UPDATE rows."""
    __tablename__ = "credits_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    amount: Mapped[int] = mapped_column(Integer)  # + grant/purchase, - consumption
    type: Mapped[str] = mapped_column(String(50))  # subscription_grant|purchase|consumption|refund
    description: Mapped[str | None] = mapped_column(String(512))
    reference_id: Mapped[str | None] = mapped_column(String(255), index=True)
    balance_after: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
