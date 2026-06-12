from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Product, Review, RoleName, User
from app.schemas import Message, RatingSummary, ReviewCreate, ReviewOut, ReviewUpdate
from app.services import product_rating_summary

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def add_review(
    payload: ReviewCreate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Review:
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    exists = db.scalar(select(Review).where(Review.user_id == current_user.id, Review.product_id == payload.product_id))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already reviewed this product")

    review = Review(user_id=current_user.id, **payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot update this review")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, key, value)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/{review_id}", response_model=Message)
def delete_review(
    review_id: int,
    current_user: User = Depends(require_roles(RoleName.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Message:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this review")

    db.delete(review)
    db.commit()
    return Message(message="Review deleted")


@router.get("/products/{product_id}/ratings", response_model=RatingSummary)
def product_ratings(product_id: int, db: Session = Depends(get_db)) -> RatingSummary:
    if db.get(Product, product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    average, count = product_rating_summary(db, product_id)
    return RatingSummary(product_id=product_id, average_rating=average, total_reviews=count)

