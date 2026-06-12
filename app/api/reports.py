from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Order, Payment, PaymentStatus, Product, RoleName, User, Vendor
from app.schemas import AdminDashboard

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/admin-dashboard", response_model=AdminDashboard)
def admin_dashboard(
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> AdminDashboard:
    from app.models import User as UserModel

    revenue = (
        db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == PaymentStatus.SUCCESS))
        or Decimal("0.00")
    )
    return AdminDashboard(
        total_users=db.scalar(select(func.count(UserModel.id))) or 0,
        total_vendors=db.scalar(select(func.count(Vendor.id))) or 0,
        total_products=db.scalar(select(func.count(Product.id))) or 0,
        total_orders=db.scalar(select(func.count(Order.id))) or 0,
        revenue_report=revenue,
    )

