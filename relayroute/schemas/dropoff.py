"""Dropoff point schemas."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DropoffSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city_id: str
    zone_id: str
    lat: float
    lng: float
    address: str
    capacity: int
    current_load: int
    status: str


class DropoffStatusUpdate(BaseModel):
    status: Literal["active", "full", "disabled"]


class DropoffStatusResponse(BaseModel):
    dropoff_id: str
    status: str
    affected_orders: list[str]
