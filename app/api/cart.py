from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Cart, CartItem, Product, RoleName, User
from app.schemas import CartItemCreate, CartItemUpdate, CartOut, Message
from app.services import cart_total, get_or_create_cart, require_product_available

router = APIRouter(prefix="/cart", tags=["Cart Management"])


def load_cart(db: Session, user_id: int) -> Cart:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == user_id)
    )
    if cart is None:
        cart = get_or_create_cart(db, user_id)
        db.commit()
        db.refresh(cart)
    return cart


@router.post("/items", response_model=CartOut)
def add_to_cart(
    payload: CartItemCreate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> CartOut:
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_product_available(product, payload.quantity)

    cart = get_or_create_cart(db, current_user.id)
    item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id))
    if item:
        require_product_available(product, item.quantity + payload.quantity)
        item.quantity += payload.quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))

    db.commit()
    cart = load_cart(db, current_user.id)
    return CartOut.model_validate(cart).model_copy(update={"total_amount": cart_total(cart)})


@router.get("", response_model=CartOut)
def view_cart(
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> CartOut:
    cart = load_cart(db, current_user.id)
    return CartOut.model_validate(cart).model_copy(update={"total_amount": cart_total(cart)})


@router.put("/items/{item_id}", response_model=CartOut)
def update_quantity(
    item_id: int,
    payload: CartItemUpdate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> CartOut:
    cart = load_cart(db, current_user.id)
    item = next((cart_item for cart_item in cart.items if cart_item.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    require_product_available(item.product, payload.quantity)

    item.quantity = payload.quantity
    db.commit()
    cart = load_cart(db, current_user.id)
    return CartOut.model_validate(cart).model_copy(update={"total_amount": cart_total(cart)})


@router.delete("/items/{item_id}", response_model=Message)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Message:
    cart = load_cart(db, current_user.id)
    item = next((cart_item for cart_item in cart.items if cart_item.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    db.delete(item)
    db.commit()
    return Message(message="Item removed from cart")

