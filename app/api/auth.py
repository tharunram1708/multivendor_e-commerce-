from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Role, RoleName, User
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    Message,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if payload.role == RoleName.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super admin users must be created from server configuration",
        )

    email_exists = db.scalar(select(User).where(User.email == payload.email))
    if email_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = db.scalar(select(Role).where(Role.name == payload.role))
    if role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Role is not configured")

    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    audit(db, action="user_login", user=user, entity_type="users", entity_id=user.id, request=request)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_data = decode_token(payload.refresh_token, expected_type="refresh")
    user = db.get(User, int(token_data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return Message(message="Password changed successfully")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    reset_token = token_urlsafe(32)

    if user is not None:
        settings = get_settings()
        user.reset_token_hash = hash_password(reset_token)
        user.reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)
        db.commit()

    return ForgotPasswordResponse(
        message="If the email exists, a reset token has been generated",
        reset_token=reset_token,
    )


@router.post("/reset-password", response_model=Message)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> Message:
    users = db.scalars(select(User).where(User.reset_token_hash.is_not(None))).all()
    matched_user = None
    for user in users:
        if user.reset_token_hash and verify_password(payload.reset_token, user.reset_token_hash):
            matched_user = user
            break

    if matched_user is None or matched_user.reset_token_expires_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    if matched_user.reset_token_expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token expired")

    matched_user.password_hash = hash_password(payload.new_password)
    matched_user.reset_token_hash = None
    matched_user.reset_token_expires_at = None
    db.commit()
    return Message(message="Password reset successfully")

