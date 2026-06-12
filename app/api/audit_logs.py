from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import AuditLog, RoleName, User
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogOut])
def get_audit_logs(
    page: int = 1,
    size: int = 50,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    query = select(AuditLog).order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)
    return list(db.scalars(query).all())

