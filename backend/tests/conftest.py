"""Tests never use DATABASE_URL or .env: an explicit test database is mandatory."""

import os
import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.dependencies import AdminUser, CurrentUser
from app.application import create_app
from app.core.config import Settings
from app.db import get_session


@pytest.fixture(scope="session")
def database_url():
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.fail("Set TEST_DATABASE_URL or use scripts/test_backend.py; no database fallback")
    url = make_url(value)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a PostgreSQL database ending in _test")
    if value == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL must not equal DATABASE_URL")
    return value


@pytest.fixture(scope="session")
def engine(database_url):
    # A unique schema prevents this suite from modifying pre-existing tables, even in a test DB.
    schema = "auth_test_" + uuid4().hex
    control = create_engine(database_url)
    with control.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    isolated = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with isolated.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield isolated
    finally:
        isolated.dispose()
        with control.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        control.dispose()


@pytest.fixture
def session(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as db_session:
            yield db_session
        transaction.rollback()


@pytest.fixture
def settings(database_url):
    return Settings(
        _env_file=None,
        database_url=database_url,
        jwt_secret_key=secrets.token_hex(32),
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        jwt_issuer="dealership-api-test",
        jwt_audience="dealership-web-test",
        cors_origins=["http://localhost:5173"],
    )


@pytest.fixture
def app(settings, session):
    application = create_app(settings)

    def test_session():
        yield session

    application.dependency_overrides[get_session] = test_session

    # Test-only probes exercise the real dependencies; these are not production endpoints.
    @application.get("/_test/me")
    def me(user: CurrentUser):
        return {"id": str(user.id), "role": user.role}

    @application.get("/_test/admin")
    def admin(user: AdminUser):
        return {"id": str(user.id)}

    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
