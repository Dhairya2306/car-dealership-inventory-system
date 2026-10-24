"""Account persistence and password verification, independent of HTTP response handling."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, password_hasher, verify_password
from app.models import Role, User


class DuplicateEmailError(Exception):
    pass


def register_user(session: Session, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password), role=Role.USER)
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # Enforce uniqueness in the database, including simultaneous registrations.
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_users_email":
            raise DuplicateEmailError from None
        raise
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == email))
    if not verify_password(password, user.password_hash if user else None):
        return None
    assert user is not None
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        session.commit()
    return user
