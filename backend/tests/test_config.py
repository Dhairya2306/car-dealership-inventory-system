import pytest
from pydantic import ValidationError

from app.core.config import Settings


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
