from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import OrderItem, Payment, PaymentStatus, Product, RoleName, User, Vendor
from app.schemas import VendorCreate, VendorDashboard, VendorOut, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["Vendor Management"])


@router.post("/profile", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
def create_vendor_profile(
    payload: VendorCreate,
    current_user: User = Depends(require_roles(RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Vendor:
    exists = db.scalar(select(Vendor).where(Vendor.user_id == current_user.id))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vendor profile already exists")

    vendor = Vendor(user_id=current_user.id, **payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/profile", response_model=VendorOut)
def view_vendor_profile(
    current_user: User = Depends(require_roles(RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Vendor:
    vendor = db.scalar(select(Vendor).where(Vendor.user_id == current_user.id))
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
    return vendor


@router.put("/profile", response_model=VendorOut)
def update_vendor_profile(
    payload: VendorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Vendor:
    vendor = db.scalar(select(Vendor).where(Vendor.user_id == current_user.id))
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and current_user.role.name != RoleName.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can update status")

    for key, value in data.items():
        setattr(vendor, key, value)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.put("/profile/{vendor_id}", response_model=VendorOut)
def update_vendor_by_admin(
    vendor_id: int,
    payload: VendorUpdate,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, key, value)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/profile/{vendor_id}", response_model=VendorOut)
def get_vendor_by_id(
    vendor_id: int,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.get("/dashboard", response_model=VendorDashboard)
def vendor_dashboard(
    current_user: User = Depends(require_roles(RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> VendorDashboard:
    vendor = db.scalar(select(Vendor).where(Vendor.user_id == current_user.id))
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

    total_products = db.scalar(select(func.count(Product.id)).where(Product.vendor_id == vendor.id)) or 0
    total_orders = (
        db.scalar(select(func.count(func.distinct(OrderItem.order_id))).where(OrderItem.vendor_id == vendor.id)) or 0
    )
    revenue = (
        db.scalar(
            select(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .join(Payment, Payment.order_id == OrderItem.order_id)
            .where(OrderItem.vendor_id == vendor.id, Payment.status == PaymentStatus.SUCCESS)
        )
        or Decimal("0.00")
    )
    return VendorDashboard(
        total_products=total_products,
        total_orders=total_orders,
        revenue_generated=revenue,
    )
