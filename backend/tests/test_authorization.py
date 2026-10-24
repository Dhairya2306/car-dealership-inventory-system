from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest

from app.models import Role, User

ACCOUNT = {"email": "auth@example.com", "password": "A long test password!"}


@pytest.fixture
def account(client):
    user = client.post("/api/auth/register", json=ACCOUNT).json()
    token = client.post("/api/auth/login", json=ACCOUNT).json()["access_token"]
    return user, token


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def signed_token(settings, user_id, **changes):
    claims = {
        "sub": user_id,
        "iat": datetime.now(UTC) - timedelta(minutes=2),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    } | changes
    return jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")


def test_current_user_requires_bearer_authentication(client):
    for authorization in [None, "Basic dXNlcjpwYXNz", "Bearer"]:
        response = client.get(
            "/_test/me", headers={"Authorization": authorization} if authorization else {}
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_valid_token_resolves_current_user(client, account):
    user, token = account
    response = client.get("/_test/me", headers=headers(token))
    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "role": "user"}


@pytest.mark.parametrize(
    "kind",
    [
        "malformed",
        "signature",
        "expired",
        "subject",
        "missing_exp",
        "issuer",
        "audience",
        "algorithm",
        "future_iat",
    ],
)
def test_invalid_jwt_is_rejected(client, account, settings, kind):
    user, token = account
    if kind == "malformed":
        token = "not.a.jwt"
    elif kind == "signature":
        claims = jwt.decode(token, options={"verify_signature": False})
        token = jwt.encode(claims, "wrong-secret-" * 4, algorithm="HS256")
    elif kind == "expired":
        token = signed_token(settings, user["id"], exp=datetime.now(UTC) - timedelta(seconds=10))
    elif kind == "subject":
        token = signed_token(settings, "not-a-uuid")
    elif kind == "missing_exp":
        claims = jwt.decode(token, options={"verify_signature": False})
        del claims["exp"]
        token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    elif kind == "issuer":
        token = signed_token(settings, user["id"], iss="another-app")
    elif kind == "audience":
        token = signed_token(settings, user["id"], aud="another-client")
    elif kind == "algorithm":
        claims = jwt.decode(token, options={"verify_signature": False})
        token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS384")
    else:
        token = signed_token(settings, user["id"], iat=datetime.now(UTC) + timedelta(hours=1))
    response = client.get("/_test/me", headers=headers(token))
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


def test_token_for_nonexistent_user_is_rejected(client, settings):
    response = client.get("/_test/me", headers=headers(signed_token(settings, str(uuid4()))))
    assert response.status_code == 401


def test_normal_user_cannot_access_admin_dependency(client, account):
    response = client.get("/_test/admin", headers=headers(account[1]))
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_role_is_read_from_database_on_every_request(client, account, session):
    user, token = account
    stored_user = session.get(User, UUID(user["id"]))
    stored_user.role = Role.ADMIN
    session.commit()
    assert client.get("/_test/admin", headers=headers(token)).status_code == 200
    stored_user.role = Role.USER
    session.commit()
    assert client.get("/_test/admin", headers=headers(token)).status_code == 403


def test_admin_claim_cannot_override_database_role(client, account, settings):
    token = signed_token(settings, account[0]["id"], role="admin")
    assert client.get("/_test/admin", headers=headers(token)).status_code == 403


def test_deleted_user_token_is_rejected(client, account, session):
    user, token = account
    session.delete(session.get(User, UUID(user["id"])))
    session.commit()
    assert client.get("/_test/me", headers=headers(token)).status_code == 401
