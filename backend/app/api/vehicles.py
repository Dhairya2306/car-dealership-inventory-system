"""Authenticated vehicle inventory routes."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models import Vehicle
from app.schemas.vehicle import Pagination, VehicleCreate, VehiclePage, VehicleResponse
from app.services import vehicles

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate, session: SessionDependency, user: CurrentUser
) -> Vehicle:
    return vehicles.create_vehicle(session, payload)


@router.get("", response_model=VehiclePage)
def list_vehicles(
    pagination: Annotated[Pagination, Query()], session: SessionDependency, user: CurrentUser
) -> VehiclePage:
    items, total = vehicles.list_vehicles(session, pagination)
    return VehiclePage(items=items, total=total, **pagination.model_dump())
