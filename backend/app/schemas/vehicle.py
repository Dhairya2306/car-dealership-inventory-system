"""Vehicle inputs and paginated responses; prices serialize as decimal strings."""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_QUANTITY = 2_147_483_647


class VehicleDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)


class VehicleCreate(VehicleDetails):
    quantity: int = Field(ge=0, le=MAX_QUANTITY, strict=True)


class VehicleUpdate(VehicleDetails):
    """Replace descriptive fields only; stock is changed through dedicated operations."""


class RestockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0, le=MAX_QUANTITY, strict=True)


class VehicleResponse(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=2_147_483_647)


class VehicleSearch(Pagination):
    model_config = ConfigDict(str_strip_whitespace=True)

    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    min_price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    max_price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def valid_price_range(self) -> Self:
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price must not exceed max_price")
        return self


class VehiclePage(BaseModel):
    items: list[VehicleResponse]
    total: int
    limit: int
    offset: int
