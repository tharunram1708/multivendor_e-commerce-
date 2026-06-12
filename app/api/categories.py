from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Category, RoleName, User
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate, Message

router = APIRouter(prefix="/categories", tags=["Category Management"])


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryOut])
def get_categories(search: str | None = None, db: Session = Depends(get_db)) -> list[Category]:
    query = select(Category).order_by(Category.name)
    if search:
        query = query.where(Category.name.ilike(f"%{search}%"))
    return list(db.scalars(query).all())


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=Message)
def delete_category(
    category_id: int,
    _: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> Message:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(category)
    db.commit()
    return Message(message="Category deleted")

