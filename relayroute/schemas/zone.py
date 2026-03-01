"""Zone schemas."""
from pydantic import BaseModel, ConfigDict


class ZoneSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city_id: str
    name: str
    restaurant_count: int


class ZoneTopologySummary(ZoneSummary):
    """Zone with boundaries for map/topology responses."""

    boundaries: dict


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


class ZoneRestaurantSummary(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class ZoneDropoffSummary(BaseModel):
    id: str
    status: str
    current_load: int
    capacity: int


class ZonePartnerSummary(BaseModel):
    partner_id: str
    name: str
    status: str


class ZoneActiveOrderSummary(BaseModel):
    order_id: str
    status: str


class ZoneDetailResponse(BaseModel):
    zone_id: str
    city_id: str
    name: str
    boundaries: dict
    restaurant_count: int
    restaurants: list[ZoneRestaurantSummary]
    dropoff_points: list[ZoneDropoffSummary]
    active_partners: list[ZonePartnerSummary]
    active_orders: list[ZoneActiveOrderSummary]


class ZonePartnersResponse(BaseModel):
    zone_id: str
    partners: list[ZonePartnerSummary]


class ZoneDropoffPointSummary(BaseModel):
    dropoff_id: str
    status: str
    current_load: int
    capacity: int
    lat: float
    lng: float


class ZoneDropoffsResponse(BaseModel):
    zone_id: str
    dropoff_points: list[ZoneDropoffPointSummary]


class ZoneOrderSummary(BaseModel):
    order_id: str
    status: str
    current_dropoff_id: str | None
    remaining_handoffs: int


class ZoneOrdersResponse(BaseModel):
    zone_id: str
    orders: list[ZoneOrderSummary]
