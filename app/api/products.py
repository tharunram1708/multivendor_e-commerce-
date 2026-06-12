from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Category, Product, ProductStatus, RoleName, User, Vendor
from app.schemas import Message, ProductCreate, ProductOut, ProductUpdate
from app.services import audit, require_product_owner_or_admin, vendor_for_product_create

router = APIRouter(prefix="/products", tags=["Product Management"])


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def add_product(
    payload: ProductCreate,
    request: Request,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Product:
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    vendor = vendor_for_product_create(db, current_user, payload.vendor_id)
    product_data = payload.model_dump(exclude={"vendor_id"})
    product = Product(**product_data, vendor_id=vendor.id)
    db.add(product)
    db.flush()
    audit(
        db,
        action="product_creation",
        user=current_user,
        entity_type="products",
        entity_id=product.id,
        details=product.name,
        request=request,
    )
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def get_all_products(
    search: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    vendor_id: int | None = None,
    status_filter: ProductStatus | None = None,
    page: int = 1,
    size: int = 20,
    sort_by: Literal["name", "price", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> list[Product]:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    query = select(Product)

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    if category_id:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if vendor_id:
        query = query.where(Product.vendor_id == vendor_id)
    if status_filter:
        query = query.where(Product.status == status_filter)

    sort_column = getattr(Product, sort_by)
    query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
    query = query.offset((page - 1) * size).limit(size)
    return list(db.scalars(query).all())


@router.get("/vendor/{vendor_id}", response_model=list[ProductOut])
def get_products_by_vendor(vendor_id: int, db: Session = Depends(get_db)) -> list[Product]:
    if db.get(Vendor, vendor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return list(db.scalars(select(Product).where(Product.vendor_id == vendor_id)).all())


@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    request: Request,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_product_owner_or_admin(current_user, product)

    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for key, value in data.items():
        setattr(product, key, value)

    audit(
        db,
        action="product_update",
        user=current_user,
        entity_type="products",
        entity_id=product.id,
        details=product.name,
        request=request,
    )
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=Message)
def delete_product(
    product_id: int,
    request: Request,
    current_user: User = Depends(require_roles(RoleName.SUPER_ADMIN, RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Message:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_product_owner_or_admin(current_user, product)

    product.status = ProductStatus.INACTIVE
    audit(
        db,
        action="product_delete",
        user=current_user,
        entity_type="products",
        entity_id=product.id,
        details=product.name,
        request=request,
    )
    db.commit()
    return Message(message="Product marked inactive")
