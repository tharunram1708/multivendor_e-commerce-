from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import RoleName, User, Vendor, VendorStatus


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_roles(*allowed_roles: RoleName) -> Callable[[User], User]:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name
        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action",
            )
        return current_user

    return checker


def get_current_vendor(
    current_user: User = Depends(require_roles(RoleName.VENDOR)),
    db: Session = Depends(get_db),
) -> Vendor:
    vendor = db.scalar(select(Vendor).where(Vendor.user_id == current_user.id))
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile is not created yet",
        )
    if vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account is not active",
        )
    return vendor

