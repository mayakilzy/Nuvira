"""Admin router — guarded by require_admin."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import require_admin
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [{"id": u.id, "email": u.email, "role": u.role,
             "is_active": u.is_active, "created_at": u.created_at} for u in users]


@router.get("/stats")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"total_users": db.query(User).count()}
