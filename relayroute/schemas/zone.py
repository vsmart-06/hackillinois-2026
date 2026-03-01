"""Zone schemas."""
from pydantic import BaseModel, ConfigDict, Field


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
    utilization_ratio: float = Field(
        description=(
            "Current load as a fraction of total capacity across all drop-off points in the zone. "
            "0.0 is empty, 1.0 is fully saturated."
        )
    )
    load_status: str = Field(description="Human-readable load classification: low, moderate, or high.")
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


class ZoneDropoffBase(BaseModel):
    status: str
    current_load: int
    capacity: int


class ZoneDropoffSummary(ZoneDropoffBase):
    id: str
    lat: float
    lng: float


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


class ZoneDropoffPointSummary(ZoneDropoffBase):
    dropoff_id: str
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
