from unittest.mock import Mock

from sqlalchemy.exc import OperationalError

from app.db import get_session


def test_health_queries_postgresql(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_failure_is_503_without_database_details(client, app):
    session = Mock()
    session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("private database URL")
    )
    app.dependency_overrides[get_session] = lambda: session
    response = client.get("/api/health")
    assert response.status_code == 503
    assert "private" not in response.text
    session.rollback.assert_called_once()


def test_cors_accepts_frontend_and_rejects_other_origins(client):
    for origin, expected in [("http://localhost:5173", 200), ("http://untrusted.example", 400)]:
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == expected
        if expected == 200:
            assert response.headers["access-control-allow-origin"] == origin
        else:
            assert "access-control-allow-origin" not in response.headers


def test_login_database_failure_has_safe_retryable_error(client, app):
    session = Mock()
    session.scalar.side_effect = OperationalError(
        "private SQL", {}, Exception("private database password")
    )
    app.dependency_overrides[get_session] = lambda: session
    response = client.post(
        "/api/auth/login", json={"email": "driver@example.com", "password": "test-password"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable. Please try again."}
    assert "private" not in response.text
