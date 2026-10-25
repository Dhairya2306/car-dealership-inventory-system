"""Validated environment configuration; no credentials have fallback values."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True)

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if (
            url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}
            or not url.database
        ):
            raise ValueError("DATABASE_URL must use PostgreSQL and name a database")
        # Hosted URLs usually omit the driver. Always select the installed psycopg 3 driver.
        # URL objects preserve encoded credentials and query options such as sslmode.
        return SecretStr(
            url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
        )


class Settings(DatabaseSettings):
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_issuer: str = "dealership-api"
    jwt_audience: str = "dealership-web"
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_blank_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().strip()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 non-padding characters")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return origins
