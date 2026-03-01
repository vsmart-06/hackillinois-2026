"""Zone schemas."""
from pydantic import BaseModel, ConfigDict


class ZoneSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city_id: str
    name: str
    restaurant_count: int


class ZoneLoadResponse(BaseModel):
    zone_id: str
    city_id: str
    dropoff_count: int
    active_dropoffs: int
    full_dropoffs: int
    disabled_dropoffs: int
    total_capacity: int
    current_load: int
    utilization_ratio: float
    partners_available: int
    partners_carrying: int
    partners_offline: int
    orders_pending: int
    orders_in_transit: int
    orders_delivered: int
