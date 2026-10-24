"""SQLAlchemy persistence models."""

from app.models.user import Role, User
from app.models.vehicle import Vehicle

__all__ = ["Role", "User", "Vehicle"]
