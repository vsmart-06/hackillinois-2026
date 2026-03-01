"""Order request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city_id": "city_mumbai_demo01",
                "restaurant_id": "restaurant_bandra_17",
                "delivery_address": "Flat 903, A Wing, Hiranandani Powai, Mumbai 400076",
            }
        }
    )

    city_id: str
    restaurant_id: str
    delivery_address: str


class Coordinates(BaseModel):
    lat: float
    lng: float


class RelayChainStep(BaseModel):
    zone_id: str
    dropoff_point_id: str
    coords: Coordinates


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    relay_chain: list[RelayChainStep]
    estimated_handoffs: int


class OrderStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    status: str
    remaining_handoffs: int
    current_zone_id: str | None
    current_dropoff_id: str | None


class OrderListItem(BaseModel):
    order_id: str
    restaurant_id: str
    status: str
    estimated_handoffs: int
    remaining_handoffs: int
    created_at: datetime


class OrderDetailResponse(BaseModel):
    order_id: str
    city_id: str
    restaurant_id: str
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    status: str
    relay_chain: list[RelayChainStep]
    current_dropoff_id: str | None
    current_zone_id: str | None
    estimated_handoffs: int
    remaining_handoffs: int
    created_at: datetime


class RelayHistoryEvent(BaseModel):
    event: str
    partner_id: str | None
    dropoff_id: str | None
    timestamp: datetime


class RelayHistoryResponse(BaseModel):
    order_id: str
    history: list[RelayHistoryEvent]
