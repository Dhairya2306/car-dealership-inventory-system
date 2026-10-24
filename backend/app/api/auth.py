"""Account creation and JSON credential login."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import SessionDependency, SettingsDependency, unauthorized
from app.core.security import create_access_token, hash_password, password_hasher, verify_password
from app.models import Role, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: SessionDependency) -> User:
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password.get_secret_value()),
        role=Role.USER,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # The unique constraint handles concurrent registrations without a check-then-write race.
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_users_email":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
            ) from None
        raise
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, session: SessionDependency, settings: SettingsDependency
) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == str(payload.email)))
    password = payload.password.get_secret_value()
    if not verify_password(password, user.password_hash if user else None):
        raise unauthorized("Invalid email or password")
    assert user is not None
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        session.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )
