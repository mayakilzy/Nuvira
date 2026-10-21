from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.credits import CreditLedger
from app.models.user import User
from app.services import credits_service

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance")
def balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"balance": credits_service.get_balance(db, user.id)}


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(CreditLedger)
        .filter(CreditLedger.user_id == user.id)
        .order_by(CreditLedger.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id, "amount": r.amount, "type": r.type,
            "description": r.description, "balance_after": r.balance_after,
            "created_at": r.created_at,
        }
        for r in rows
    ]
