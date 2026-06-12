from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import (
    Cart,
    CartItem,
    InventoryAction,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    RoleName,
    User,
)
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import add_inventory_log, audit, cart_total, require_product_available

router = APIRouter(prefix="/orders", tags=["Order Management"])


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    request: Request,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Order:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == current_user.id)
    )
    if cart is None or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    for item in cart.items:
        require_product_available(item.product, item.quantity)

    order = Order(
        user_id=current_user.id,
        total_amount=cart_total(cart),
        shipping_address=payload.shipping_address,
    )
    db.add(order)
    db.flush()

    for item in cart.items:
        product: Product = item.product
        subtotal = product.price * item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                vendor_id=product.vendor_id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal,
            )
        )
        product.quantity -= item.quantity
        add_inventory_log(
            db,
            product=product,
            quantity=item.quantity,
            action=InventoryAction.ORDER_DEDUCTION,
            note=f"Order #{order.id}",
        )
        db.delete(item)

    audit(
        db,
        action="order_creation",
        user=current_user,
        entity_type="orders",
        entity_id=order.id,
        request=request,
    )
    db.commit()
    return get_order_or_404(db, order.id)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    order = get_order_or_404(db, order_id)
    if current_user.role.name == RoleName.CUSTOMER and order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot cancel this order")
    if order.status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order cannot be cancelled now")

    order.status = OrderStatus.CANCELLED
    for item in order.items:
        product = db.get(Product, item.product_id)
        if product:
            product.quantity += item.quantity
            add_inventory_log(
                db,
                product=product,
                quantity=item.quantity,
                action=InventoryAction.CANCELLATION_RETURN,
                note=f"Order #{order.id} cancelled",
            )

    audit(
        db,
        action="order_cancellation",
        user=current_user,
        entity_type="orders",
        entity_id=order.id,
        request=request,
    )
    db.commit()
    return get_order_or_404(db, order.id)


@router.get("/history", response_model=list[OrderOut])
def order_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
    if current_user.role.name == RoleName.CUSTOMER:
        query = query.where(Order.user_id == current_user.id)
    elif current_user.role.name == RoleName.VENDOR:
        vendor = current_user.vendor_profile
        if vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
        query = query.join(OrderItem).where(OrderItem.vendor_id == vendor.id).distinct()
    return list(db.scalars(query).all())


@router.get("/{order_id}", response_model=OrderOut)
def order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    order = get_order_or_404(db, order_id)
    if current_user.role.name == RoleName.CUSTOMER and order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this order")
    if current_user.role.name == RoleName.VENDOR:
        vendor = current_user.vendor_profile
        if vendor is None or all(item.vendor_id != vendor.id for item in order.items):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this order")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Order:
    order = get_order_or_404(db, order_id)
    order.status = payload.status
    db.commit()
    return get_order_or_404(db, order.id)

