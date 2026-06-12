from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Product, RoleName, User, Wishlist
from app.schemas import Message, WishlistCreate, WishlistOut

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.post("", response_model=WishlistOut, status_code=status.HTTP_201_CREATED)
def add_wishlist(
    payload: WishlistCreate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Wishlist:
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    exists = db.scalar(
        select(Wishlist).where(Wishlist.user_id == current_user.id, Wishlist.product_id == payload.product_id)
    )
    if exists:
        return exists

    item = Wishlist(user_id=current_user.id, product_id=payload.product_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{product_id}", response_model=Message)
def remove_wishlist(
    product_id: int,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Message:
    item = db.scalar(select(Wishlist).where(Wishlist.user_id == current_user.id, Wishlist.product_id == product_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    db.delete(item)
    db.commit()
    return Message(message="Wishlist item removed")


@router.get("", response_model=list[WishlistOut])
def view_wishlist(
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> list[Wishlist]:
    return list(
        db.scalars(
            select(Wishlist)
            .options(selectinload(Wishlist.product))
            .where(Wishlist.user_id == current_user.id)
            .order_by(Wishlist.id.desc())
        ).all()
    )

