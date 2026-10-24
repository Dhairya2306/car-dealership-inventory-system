import pytest

ACCOUNT = {"email": "driver@example.com", "password": "A long test password!"}


def register(client, **overrides):
    return client.post("/api/auth/register", json=ACCOUNT | overrides)


def test_registration_normalizes_email_and_returns_only_public_fields(client):
    response = register(client, email="  DRIVER@Example.COM  ")
    assert response.status_code == 201
    user = response.json()
    assert user["email"] == "driver@example.com"
    assert user["role"] == "user"
    assert {"id", "email", "role", "created_at", "updated_at"} == set(user)


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
