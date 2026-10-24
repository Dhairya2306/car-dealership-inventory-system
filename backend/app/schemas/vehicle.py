"""Vehicle inputs and paginated responses; prices serialize as decimal strings."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MAX_QUANTITY = 2_147_483_647


class VehicleDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)


class VehicleCreate(VehicleDetails):
    quantity: int = Field(ge=0, le=MAX_QUANTITY, strict=True)


class VehicleResponse(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class VehiclePage(BaseModel):
    items: list[VehicleResponse]
    total: int
    limit: int
    offset: int
