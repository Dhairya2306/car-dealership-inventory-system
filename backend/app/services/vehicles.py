"""Inventory persistence and transactional stock operations."""

from uuid import UUID

from sqlalchemy import Update, delete, func, select, update
from sqlalchemy.orm import Session

from app.models import Vehicle
from app.schemas.vehicle import (
    MAX_QUANTITY,
    Pagination,
    VehicleCreate,
    VehicleSearch,
    VehicleUpdate,
)


class VehicleNotFoundError(Exception):
    pass


class StockConflictError(Exception):
    pass


def create_vehicle(session: Session, payload: VehicleCreate) -> Vehicle:
    vehicle = Vehicle(**payload.model_dump())
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def list_vehicles(
    session: Session, pagination: Pagination, filters: VehicleSearch | None = None
) -> tuple[list[Vehicle], int]:
    conditions = []
    if filters is not None:
        if filters.make is not None:
            conditions.append(Vehicle.make.icontains(filters.make, autoescape=True))
        if filters.model is not None:
            conditions.append(Vehicle.model.icontains(filters.model, autoescape=True))
        if filters.category is not None:
            conditions.append(func.lower(Vehicle.category) == filters.category.lower())
        if filters.min_price is not None:
            conditions.append(Vehicle.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Vehicle.price <= filters.max_price)
    total = session.scalar(select(func.count()).select_from(Vehicle).where(*conditions))
    statement = (
        select(Vehicle)
        .where(*conditions)
        .order_by(Vehicle.created_at, Vehicle.id)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return list(session.scalars(statement)), total


def _apply_update(
    session: Session, vehicle_id: UUID, statement: Update, conflict: str | None = None
) -> Vehicle:
    vehicle = session.scalar(
        statement.returning(Vehicle), execution_options={"populate_existing": True}
    )
    if vehicle is None:
        exists = session.scalar(select(Vehicle.id).where(Vehicle.id == vehicle_id))
        session.rollback()
        if exists is None:
            raise VehicleNotFoundError
        raise StockConflictError(conflict)
    session.commit()
    return vehicle


def update_vehicle(session: Session, vehicle_id: UUID, payload: VehicleUpdate) -> Vehicle:
    # Never include quantity in this SET: a stale details form cannot undo stock changes.
    statement = update(Vehicle).where(Vehicle.id == vehicle_id).values(**payload.model_dump())
    return _apply_update(session, vehicle_id, statement)


def delete_vehicle(session: Session, vehicle_id: UUID) -> None:
    deleted = session.scalar(delete(Vehicle).where(Vehicle.id == vehicle_id).returning(Vehicle.id))
    if deleted is None:
        session.rollback()
        raise VehicleNotFoundError
    session.commit()


def purchase_vehicle(session: Session, vehicle_id: UUID) -> Vehicle:
    # PostgreSQL serializes updates to this row and rechecks quantity after waiting for its lock.
    statement = (
        update(Vehicle)
        .where(Vehicle.id == vehicle_id, Vehicle.quantity > 0)
        .values(quantity=Vehicle.quantity - 1)
    )
    return _apply_update(session, vehicle_id, statement, "Vehicle is out of stock")


def restock_vehicle(session: Session, vehicle_id: UUID, quantity: int) -> Vehicle:
    statement = (
        update(Vehicle)
        .where(Vehicle.id == vehicle_id, Vehicle.quantity <= MAX_QUANTITY - quantity)
        .values(quantity=Vehicle.quantity + quantity)
    )
    return _apply_update(session, vehicle_id, statement, "Stock limit would be exceeded")
