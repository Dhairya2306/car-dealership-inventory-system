"""ASGI entry point; missing or invalid environment configuration fails at startup."""

from app.application import create_app
from app.core.config import Settings

app = create_app(Settings())
