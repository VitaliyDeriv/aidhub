from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import Role, User
from app.schemas import UserOut, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


def _load_authorized(db: DbSession, current: User, user_id: int) -> User:
    """Горизонтальний контроль доступу (захист від IDOR).

    Чужий профіль доступний лише адміністратору. Перевірка прав іде
    раніше за пошук, тож звичайний користувач не дізнається, чи існує id.
    """
    if current.role != Role.ADMIN and current.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access to another user's data is forbidden")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("/me", response_model=UserOut)
def read_me(current: CurrentUser):
    return current


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, current: CurrentUser, db: DbSession):
    return _load_authorized(db, current, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, current: CurrentUser, db: DbSession):
    user = _load_authorized(db, current, user_id)
    return users_service.update_user(db, user, payload)
