"""Authenticated vehicle inventory routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import AdminUser, CurrentUser, SessionDependency
from app.models import Vehicle
from app.schemas.vehicle import (
    Pagination,
    RestockRequest,
    VehicleCreate,
    VehiclePage,
    VehicleResponse,
    VehicleSearch,
    VehicleUpdate,
)
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


# Keep static routes ahead of parameterized IDs when adding future vehicle routes.
@router.get("/search", response_model=VehiclePage)
def search_vehicles(
    filters: Annotated[VehicleSearch, Query()], session: SessionDependency, user: CurrentUser
) -> VehiclePage:
    items, total = vehicles.list_vehicles(session, filters, filters)
    return VehiclePage(items=items, total=total, limit=filters.limit, offset=filters.offset)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID, payload: VehicleUpdate, session: SessionDependency, user: CurrentUser
) -> Vehicle:
    try:
        return vehicles.update_vehicle(session, vehicle_id, payload)
    except vehicles.VehicleNotFoundError:
        raise HTTPException(status_code=404, detail="Vehicle not found") from None


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: UUID, session: SessionDependency, user: AdminUser) -> Response:
    try:
        vehicles.delete_vehicle(session, vehicle_id)
    except vehicles.VehicleNotFoundError:
        raise HTTPException(status_code=404, detail="Vehicle not found") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{vehicle_id}/purchase", response_model=VehicleResponse)
def purchase_vehicle(vehicle_id: UUID, session: SessionDependency, user: CurrentUser) -> Vehicle:
    try:
        return vehicles.purchase_vehicle(session, vehicle_id)
    except vehicles.VehicleNotFoundError:
        raise HTTPException(status_code=404, detail="Vehicle not found") from None
    except vehicles.StockConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/{vehicle_id}/restock", response_model=VehicleResponse)
def restock_vehicle(
    vehicle_id: UUID, payload: RestockRequest, session: SessionDependency, user: AdminUser
) -> Vehicle:
    try:
        return vehicles.restock_vehicle(session, vehicle_id, payload.quantity)
    except vehicles.VehicleNotFoundError:
        raise HTTPException(status_code=404, detail="Vehicle not found") from None
    except vehicles.StockConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
