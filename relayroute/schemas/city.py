"""City setup schemas."""
from pydantic import BaseModel

from relayroute.schemas.zone import ZoneSummary
from relayroute.schemas.restaurant import RestaurantSummary
from relayroute.schemas.dropoff import DropoffSummary


class CitySetupRequest(BaseModel):
    city_name: str
    epsilon_km: float = 0.5
    min_restaurants_per_zone: int = 10
    dropoff_spacing_km: float = 0.3
    dropoff_capacity: int = 20


class CitySetupResponse(BaseModel):
    city_id: str
    api_key: str
    zones: list[ZoneSummary]
    restaurants: list[RestaurantSummary]
    dropoff_points: list[DropoffSummary]
    zone_reasoning: str


class CitySummary(BaseModel):
    city_id: str
    city_name: str
    zone_count: int
    active_partners: int


class CityListResponse(BaseModel):
    cities: list[CitySummary]


class CityTopologyResponse(BaseModel):
    city_id: str
    city_name: str
    zones: list[ZoneSummary]
    restaurants: list[RestaurantSummary]
    dropoff_points: list[DropoffSummary]
    zone_reasoning: str
