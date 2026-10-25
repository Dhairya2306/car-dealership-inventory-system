import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import DatabaseSettings, Settings


@pytest.mark.parametrize(
    "changes",
    [
        {"jwt_secret_key": "short"},
        {"jwt_secret_key": " " * 32},
        {"jwt_algorithm": "none"},
        {"database_url": "sqlite:///test.db"},
        {"access_token_expire_minutes": 0},
        {"cors_origins": ["*"]},
    ],
)
def test_invalid_configuration_fails_early(changes):
    values = {
        "database_url": "postgresql+psycopg://localhost/config_test",
        "jwt_secret_key": "configuration-test-only-secret-" * 2,
    } | changes
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_hosted_postgresql_url_preserves_credentials_and_tls_options(scheme):
    # Synthetic credentials deliberately include URL-encoded reserved characters.
    value = f"{scheme}://example:p%40ss%2Fword%25@db.example:5432/dealership?sslmode=require"
    settings = DatabaseSettings(_env_file=None, database_url=value)
    url = make_url(settings.database_url.get_secret_value())
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "example"
    assert url.password == "p@ss/word%"
    assert url.host == "db.example"
    assert url.port == 5432
    assert url.database == "dealership"
    assert url.query == {"sslmode": "require"}
    assert "p%40ss" not in repr(settings)


def test_hosted_database_environment_overrides_dotenv(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql+psycopg://localhost/local_test\n")
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/hosted_test")
    settings = DatabaseSettings(_env_file=env_file)
    assert settings.database_url.get_secret_value() == "postgresql+psycopg://db.example/hosted_test"


@pytest.mark.parametrize(
    "value", ["not-a-url", "postgresql+psycopg2://localhost/test", "mysql://localhost/test"]
)
def test_unsupported_database_urls_are_rejected(value):
    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None, database_url=value)


def test_configuration_errors_do_not_print_secret_inputs():
    secret = "synthetic-secret-never-log"
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(_env_file=None, database_url=f"mysql://user:{secret}@db.example/test")
    assert secret not in str(error.value)
