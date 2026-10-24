from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.application import create_app
from app.core.security import verify_password
from app.models import Role, User

ACCOUNT = {"email": "driver@example.com", "password": "A long test password!"}


def register(client, **overrides):
    return client.post("/api/auth/register", json=ACCOUNT | overrides)


def test_registration_normalizes_email_and_returns_only_public_fields(client):
    response = register(client, email="  DRIVER@Example.COM  ")
    assert response.status_code == 201
    user = response.json()
    assert user["email"] == "driver@example.com"
    assert user["role"] == "user"
    assert {"id", "email", "name", "role", "created_at", "updated_at"} == set(user)
    assert user["name"] is None


def test_registration_persists_name_and_me_returns_profile(client):
    response = register(client, name="  Alex Morgan  ")
    assert response.status_code == 201
    token = client.post("/api/auth/login", json=ACCOUNT).json()["access_token"]
    profile = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json() == response.json()
    assert profile.json()["name"] == "Alex Morgan"


@pytest.mark.parametrize("name", [" ", "x" * 101])
def test_registration_rejects_invalid_name(client, name):
    assert register(client, name=name).status_code == 422


def test_me_requires_valid_authentication(client):
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    )


def test_duplicate_normalized_email_returns_conflict(client):
    assert register(client).status_code == 201
    response = register(client, email="DRIVER@EXAMPLE.COM")
    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_login_returns_bearer_token(client):
    assert register(client).status_code == 201
    response = client.post("/api/auth/login", json=ACCOUNT)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.parametrize("email", ["driver@example.com", "missing@example.com"])
def test_incorrect_credentials_return_generic_error(client, email):
    register(client)
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "Incorrect password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers["www-authenticate"] == "Bearer"


def test_registration_rejects_admin_role(client):
    response = register(client, role="admin")
    assert response.status_code == 422


def test_password_is_argon2_hashed_and_timestamps_are_timezone_aware(client, session):
    assert register(client).status_code == 201
    user = session.scalar(select(User).where(User.email == ACCOUNT["email"]))
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != ACCOUNT["password"]
    assert verify_password(ACCOUNT["password"], user.password_hash)
    assert user.role == Role.USER
    assert user.created_at.utcoffset() is not None
    assert user.updated_at.utcoffset() is not None


def test_login_normalizes_email_and_issues_verified_expiring_jwt(client, settings):
    user = register(client).json()
    response = client.post("/api/auth/login", json=ACCOUNT | {"email": " DRIVER@Example.COM "})
    assert response.status_code == 200
    token = response.json()
    claims = jwt.decode(
        token["access_token"],
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    assert claims["sub"] == user["id"]
    assert claims["exp"] - claims["iat"] == token["expires_in"] == 1800
    assert claims["exp"] > datetime.now(UTC).timestamp()
    assert "password" not in claims and "role" not in claims


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "s3crt"},
        {"password": "x" * 129},
        {"password": None},
        {"email": "invalid"},
        {"is_admin": True},
        {"password_hash": "supplied hash"},
    ],
)
def test_invalid_registration_does_not_create_user_or_echo_password(client, session, overrides):
    payload = ACCOUNT | overrides
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert session.scalar(select(User)) is None
    assert all("input" not in error for error in response.json()["detail"])
    if isinstance(payload["password"], str):
        assert payload["password"] not in response.text


def test_duplicate_failure_does_not_poison_next_request(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert register(client, email="another@example.com").status_code == 201


def test_concurrent_duplicate_registration_is_enforced_by_postgresql(engine, settings):
    email = "concurrent@example.com"
    application = create_app(settings)
    application.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with TestClient(application) as real_client:
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(
                    executor.map(
                        lambda _: real_client.post(
                            "/api/auth/register", json=ACCOUNT | {"email": email}
                        ),
                        range(2),
                    )
                )
            assert sorted(response.status_code for response in responses) == [201, 409]
            assert (
                real_client.post("/api/auth/login", json=ACCOUNT | {"email": email}).status_code
                == 200
            )
        with engine.connect() as connection:
            assert len(connection.execute(select(User.id).where(User.email == email)).all()) == 1
    finally:
        with engine.begin() as connection:
            connection.execute(delete(User).where(User.email == email))
