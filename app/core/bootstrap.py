from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Role, RoleName, User


def ensure_default_roles(db: Session) -> None:
    for role_name in RoleName:
        exists = db.scalar(select(Role).where(Role.name == role_name))
        if exists is None:
            db.add(Role(name=role_name))
    db.commit()


def ensure_first_super_admin(db: Session) -> None:
    settings = get_settings()
    if not settings.first_super_admin_email or not settings.first_super_admin_password:
        return

    role = db.scalar(select(Role).where(Role.name == RoleName.SUPER_ADMIN))
    user = db.scalar(select(User).where(User.email == settings.first_super_admin_email))
    if role is None or user is not None:
        return

    db.add(
        User(
            email=settings.first_super_admin_email,
            full_name="Super Admin",
            password_hash=hash_password(settings.first_super_admin_password),
            role_id=role.id,
        )
    )
    db.commit()

