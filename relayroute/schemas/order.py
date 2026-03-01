"""Order request/response schemas."""
from pydantic import BaseModel, ConfigDict


class OrderRequest(BaseModel):
    city_id: str
    restaurant_id: str
    delivery_address: str


class RelayChainStep(BaseModel):
    zone_id: str
    dropoff_point_id: str
    coords: dict


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
