"""Operator CLI tests use the isolated PostgreSQL transaction, never the local .env."""

from contextlib import nullcontext
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app import cli
from app.models import Role, User

ACCOUNT = {"email": "operator-target@example.com", "password": "Only a test password!"}


@pytest.fixture
def registered(client, session):
    response = client.post("/api/auth/register", json=ACCOUNT)
    assert response.status_code == 201
    return session.get(User, UUID(response.json()["id"]))


@pytest.fixture
def cli_database(monkeypatch, session, settings):
    engine = Mock()
    monkeypatch.setattr(cli, "DatabaseSettings", lambda: settings)
    monkeypatch.setattr(cli, "build_engine", lambda url: engine)
    monkeypatch.setattr(cli, "Session", lambda engine: nullcontext(session))
    return engine


def test_operator_promotes_only_named_user_and_existing_token_gains_admin_access(
    client, session, registered
):
    other = client.post("/api/auth/register", json=ACCOUNT | {"email": "other@example.com"})
    token = client.post("/api/auth/login", json=ACCOUNT).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/_test/admin", headers=headers).status_code == 403
    before = (registered.id, registered.email, registered.password_hash, registered.created_at)
    assert cli.promote_admin(session, "  OPERATOR-TARGET@EXAMPLE.COM ") is True
    assert registered.role == Role.ADMIN
    assert before == (
        registered.id,
        registered.email,
        registered.password_hash,
        registered.created_at,
    )
    assert session.get(User, UUID(other.json()["id"])).role == Role.USER
    assert client.get("/_test/admin", headers=headers).status_code == 200


def test_promotion_is_idempotent_without_timestamp_changes(session, registered):
    assert cli.promote_admin(session, ACCOUNT["email"]) is True
    session.refresh(registered)
    timestamp = registered.updated_at
    assert cli.promote_admin(session, ACCOUNT["email"]) is False
    session.refresh(registered)
    assert registered.updated_at == timestamp


def test_cli_success_and_rerun(cli_database, registered, capsys):
    args = ["promote-admin", "--email", ACCOUNT["email"]]
    assert cli.main(args) == 0
    assert "Promoted" in capsys.readouterr().out
    assert cli.main(args) == 0
    assert "already an admin" in capsys.readouterr().out
    assert cli_database.dispose.call_count == 2


def test_cli_nonexistent_user_does_not_create_account(cli_database, session, capsys):
    assert cli.main(["promote-admin", "--email", "missing@example.com"]) == 1
    assert "No registered user" in capsys.readouterr().err
    assert session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("args", [[], ["promote-admin"], ["promote-admin", "--email", "invalid"]])
def test_cli_requires_explicit_valid_email(args, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(args)
    assert error.value.code == 2


def test_cli_database_failure_is_sanitized(cli_database, session, monkeypatch, capsys):
    def unavailable(*args, **kwargs):
        raise OperationalError("private SQL", {}, Exception("private-password"))

    monkeypatch.setattr(session, "scalar", unavailable)
    assert cli.main(["promote-admin", "--email", ACCOUNT["email"]]) == 1
    error = capsys.readouterr().err
    assert "database" in error.lower()
    assert "private" not in error
    cli_database.dispose.assert_called_once()


def test_registration_cannot_invoke_promotion(client, session):
    response = client.post("/api/auth/register", json=ACCOUNT | {"role": "admin"})
    assert response.status_code == 422
    assert session.scalar(select(func.count()).select_from(User)) == 0
    assert (
        client.post("/api/auth/promote-admin", json={"email": ACCOUNT["email"]}).status_code == 404
    )
