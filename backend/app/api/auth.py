"""Account creation and JSON credential login."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import SessionDependency, SettingsDependency, unauthorized
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import DuplicateEmailError, authenticate_user, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: SessionDependency) -> User:
    try:
        return register_user(session, str(payload.email), payload.password.get_secret_value())
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, session: SessionDependency, settings: SettingsDependency
) -> TokenResponse:
    user = authenticate_user(session, str(payload.email), payload.password.get_secret_value())
    if user is None:
        raise unauthorized("Invalid email or password")
    return TokenResponse(
        access_token=create_access_token(user.id, settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )
