from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Order, OrderStatus, Payment, PaymentStatus, RoleName, User
from app.schemas import PaymentCreate, PaymentOut

router = APIRouter(prefix="/payments", tags=["Payment Module"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Payment:
    order = db.get(Order, payload.order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot pay for this order")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be paid")

    payment = Payment(
        order_id=order.id,
        user_id=current_user.id,
        amount=order.total_amount,
        method=payload.method,
        status=payload.status,
        transaction_reference=f"MOCK-{uuid4().hex[:12].upper()}",
    )
    if payload.status == PaymentStatus.SUCCESS and order.status == OrderStatus.PENDING:
        order.status = OrderStatus.CONFIRMED

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/history", response_model=list[PaymentOut])
def payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Payment]:
    query = select(Payment).order_by(Payment.id.desc())
    if current_user.role.name == RoleName.CUSTOMER:
        query = query.where(Payment.user_id == current_user.id)
    return list(db.scalars(query).all())

