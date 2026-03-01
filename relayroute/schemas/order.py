"""Order request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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

    city_id: str = Field(description="The city identifier returned from POST /app/setup.")
    restaurant_id: str = Field(
        description="ID of the originating restaurant, returned in the restaurants array from setup or GET /app/setup."
    )
    delivery_address: str = Field(
        description="Full street address of the delivery destination. Geocoded internally to determine the destination zone."
    )


class Coordinates(BaseModel):
    lat: float
    lng: float


class RelayChainStep(BaseModel):
    zone_id: str = Field(description="The zone this step of the relay occurs in.")
    dropoff_point_id: str = Field(
        description="The drop-off box where the package should be deposited at the end of this step."
    )
    coords: Coordinates = Field(
        description="Coordinates of the drop-off point for this step. Used by partner apps for navigation."
    )


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
