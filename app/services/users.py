from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Fund, Role, User
from app.schemas import RegisterIn, UserUpdate
from app.security import DUMMY_HASH, hash_password, verify_password


class RegistrationConflict(Exception):
    """Email або назва фонду вже зайняті."""


def register_user(db: Session, payload: RegisterIn) -> User:
    taken = db.scalar(select(User.id).where(User.email == payload.email)) or db.scalar(
        select(Fund.id).where(Fund.name == payload.fund_name)
    )
    if taken:
        raise RegistrationConflict
    fund = Fund(name=payload.fund_name)
    db.add(fund)
    db.flush()
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=Role.USER.value,
        fund_id=fund.id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise RegistrationConflict from None
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, DUMMY_HASH)  # вирівнюємо час відповіді
        return None
    if not verify_password(password, user.hashed_password) or not user.is_active:
        return None
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    db.commit()
    return user


def ensure_admin(db: Session, settings: Settings) -> None:
    """Створює початкового адміністратора з ADMIN_EMAIL / ADMIN_PASSWORD."""
    if not settings.admin_email or not settings.admin_password:
        return
    email = settings.admin_email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        return
    db.add(
        User(
            email=email,
            full_name="Administrator",
            hashed_password=hash_password(settings.admin_password),
            role=Role.ADMIN.value,
        )
    )
    db.commit()
