"""
Credits service — STABLE logic, identical across every project.
Balance is always derived from the ledger (single source of truth).

Per-project you only change CREDIT_COSTS (move it to config or a DB table later
if you want it editable from the Admin panel).
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.credits import CreditLedger


class InsufficientCreditsError(Exception):
    pass


# Per-project cost table. Override/extend in your agent layer.
CREDIT_COSTS: dict[str, int] = {
    "generate_report": 10,
    "send_email": 2,
    "analyze_pdf": 5,
}


def get_balance(db: Session, user_id: int) -> int:
    total = db.query(func.coalesce(func.sum(CreditLedger.amount), 0)).filter(
        CreditLedger.user_id == user_id
    ).scalar()
    return int(total or 0)


def _add_entry(db: Session, user_id: int, amount: int, type_: str,
               description: str | None, reference_id: str | None) -> CreditLedger:
    balance_after = get_balance(db, user_id) + amount
    entry = CreditLedger(
        user_id=user_id,
        amount=amount,
        type=type_,
        description=description,
        reference_id=reference_id,
        balance_after=balance_after,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def grant(db: Session, user_id: int, amount: int, type_: str = "subscription_grant",
          description: str | None = None, reference_id: str | None = None) -> CreditLedger:
    return _add_entry(db, user_id, abs(amount), type_, description, reference_id)


def check_and_deduct(db: Session, user_id: int, amount: int,
                     description: str, reference_id: str | None = None) -> int:
    """Atomically verify balance then write a consumption entry. Returns new balance."""
    balance = get_balance(db, user_id)
    if balance < amount:
        raise InsufficientCreditsError(f"need {amount}, have {balance}")
    entry = _add_entry(db, user_id, -amount, "consumption", description, reference_id)
    return entry.balance_after
