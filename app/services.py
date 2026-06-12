from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Cart,
    CartItem,
    InventoryAction,
    InventoryLog,
    Product,
    ProductStatus,
    RoleName,
    User,
    Vendor,
)


def audit(
    db: Session,
    *,
    action: str,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    request: Request | None = None,
) -> None:
    ip_address = request.client.host if request and request.client else None
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
    )


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    return cart


def cart_total(cart: Cart) -> Decimal:
    total = Decimal("0.00")
    for item in cart.items:
        total += item.product.price * item.quantity
    return total


def require_product_available(product: Product, quantity: int) -> None:
    if product.status != ProductStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not active")
    if product.quantity < quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock")


def require_product_owner_or_admin(user: User, product: Product) -> None:
    if user.role.name == RoleName.SUPER_ADMIN:
        return
    vendor = user.vendor_profile
    if user.role.name != RoleName.VENDOR or vendor is None or product.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot modify this product")


def vendor_for_product_create(db: Session, user: User, vendor_id: int | None) -> Vendor:
    if user.role.name == RoleName.SUPER_ADMIN:
        if vendor_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="vendor_id is required for admin product creation",
            )
        vendor = db.get(Vendor, vendor_id)
    else:
        vendor = user.vendor_profile

    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def add_inventory_log(
    db: Session,
    *,
    product: Product,
    quantity: int,
    action: InventoryAction,
    note: str | None = None,
) -> None:
    db.add(
        InventoryLog(
            product_id=product.id,
            vendor_id=product.vendor_id,
            quantity=quantity,
            action=action,
            note=note,
        )
    )


def product_rating_summary(db: Session, product_id: int) -> tuple[float, int]:
    from app.models import Review

    average, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.product_id == product_id)
    ).one()
    return float(average or 0), int(count or 0)

