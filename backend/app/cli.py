"""Local operator commands. Database credentials authorize this CLI; it has no HTTP route."""

import argparse
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import DatabaseSettings
from app.db import build_engine
from app.models import Role, User


class UserNotFoundError(Exception):
    pass


def normalized_email(value: str) -> str:
    email = str(TypeAdapter(EmailStr).validate_python(value.strip())).lower()
    if len(email) > 254:
        raise ValueError("Email is too long")
    return email


def promote_admin(session: Session, email: str) -> bool:
    """Promote exactly one existing account; concurrent/rerun calls are idempotent."""
    email = normalized_email(email)
    user = session.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        raise UserNotFoundError
    if user.role == Role.ADMIN:
        return False
    user.role = Role.ADMIN
    session.commit()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    promote = commands.add_parser("promote-admin", help="Promote an existing registered user")
    promote.add_argument(
        "--email", required=True, help="Exact account email (normalized as at login)"
    )
    args = parser.parse_args(argv)
    try:
        email = normalized_email(args.email)
    except (ValidationError, ValueError):
        parser.error("A valid email of at most 254 characters is required")
    engine = None
    try:
        settings = DatabaseSettings()
        engine = build_engine(settings.database_url.get_secret_value())
        with Session(engine) as session:
            changed = promote_admin(session, email)
        print(
            f"Promoted {email} to admin." if changed else f"{email} is already an admin; unchanged."
        )
        return 0
    except UserNotFoundError:
        print("No registered user matches that email; no account was created.", file=sys.stderr)
    except (SQLAlchemyError, ValueError):
        # Never print driver exceptions, SQL parameters, connection URLs or settings values.
        print(
            "Cannot access the database. Check DATABASE_URL, connectivity and migrations.",
            file=sys.stderr,
        )
    finally:
        if engine is not None:
            engine.dispose()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
