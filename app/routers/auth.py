from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.deps import COOKIE_NAME, DbSession
from app.schemas import RegisterIn, TokenOut, UserOut
from app.security import create_access_token
from app.services import users as users_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: DbSession):
    """Реєстрація звичайного користувача разом із його фондом.

    Роль завжди `user`; адміністраторів реєстрація не створює.
    """
    try:
        return users_service.register_user(db, payload)
    except users_service.RegistrationConflict:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email or fund name already registered"
        ) from None


@router.post("/login", response_model=TokenOut)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: DbSession,
):
    user = users_service.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    token = create_access_token(user.id)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return TokenOut(access_token=token, role=user.role)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
