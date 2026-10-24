"""Inventory persistence and transactional stock operations."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Vehicle
from app.schemas.vehicle import Pagination, VehicleCreate


def create_vehicle(session: Session, payload: VehicleCreate) -> Vehicle:
    vehicle = Vehicle(**payload.model_dump())
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def list_vehicles(session: Session, pagination: Pagination) -> tuple[list[Vehicle], int]:
    total = session.scalar(select(func.count()).select_from(Vehicle))
    statement = (
        select(Vehicle)
        .order_by(Vehicle.created_at, Vehicle.id)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return list(session.scalars(statement)), total
