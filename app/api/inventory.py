from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import InventoryAction, InventoryLog, Product, RoleName, User
from app.schemas import InventoryChange, InventoryLogOut
from app.services import add_inventory_log, require_product_owner_or_admin

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


@router.post("/stock-in", response_model=InventoryLogOut)
def stock_in(
    payload: InventoryChange,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Any | None:
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_product_owner_or_admin(current_user, product)

    product.quantity += payload.quantity
    add_inventory_log(
        db,
        product=product,
        quantity=payload.quantity,
        action=InventoryAction.STOCK_IN,
        note=payload.note,
    )
    db.commit()
    return db.scalars(
        select(InventoryLog).where(InventoryLog.product_id == product.id).order_by(InventoryLog.id.desc())
    ).first()


@router.post("/stock-out", response_model=InventoryLogOut)
def stock_out(
    payload: InventoryChange,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> InventoryLog:
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_product_owner_or_admin(current_user, product)
    if product.quantity < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Low stock")

    product.quantity -= payload.quantity
    add_inventory_log(
        db,
        product=product,
        quantity=payload.quantity,
        action=InventoryAction.STOCK_OUT,
        note=payload.note,
    )
    db.commit()
    return db.scalars(
        select(InventoryLog).where(InventoryLog.product_id == product.id).order_by(InventoryLog.id.desc())
    ).first()


@router.get("/logs", response_model=list[InventoryLogOut])
def inventory_logs(
    product_id: int | None = None,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> list[InventoryLog]:
    query = select(InventoryLog).order_by(InventoryLog.id.desc())
    if product_id:
        query = query.where(InventoryLog.product_id == product_id)
    if current_user.role.name == RoleName.VENDOR:
        vendor = current_user.vendor_profile
        if vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
        query = query.where(InventoryLog.vendor_id == vendor.id)
    return list(db.scalars(query).all())

