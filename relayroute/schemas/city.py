"""City setup schemas."""
from pydantic import BaseModel, ConfigDict, Field

from relayroute.schemas.zone import ZoneSummary, ZoneTopologySummary
from relayroute.schemas.restaurant import RestaurantSummary
from relayroute.schemas.dropoff import DropoffSummary


class CitySetupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city_name": "Mumbai",
                "epsilon_km": 0.8,
                "min_restaurants_per_zone": 12,
                "dropoff_spacing_km": 0.35,
                "dropoff_capacity": 24,
            }
        }
    )

    city_name: str = Field(
        description="Name of the city to configure. Used to query restaurant locations via Google Maps."
    )
    epsilon_km: float = Field(
        default=0.5,
        description=(
            "DBSCAN clustering radius in kilometers. Controls zone granularity - smaller values produce "
            "tighter, more numerous zones. Recommended: 0.3-0.5 for dense metros like Mumbai or Bangalore, "
            "1.0-1.5 for tier-2 cities like Nagpur or Jaipur."
        ),
    )
    min_restaurants_per_zone: int = Field(
        default=10,
        description=(
            "Minimum number of restaurants required to form a zone. Clusters below this threshold are treated "
            "as noise and merged into the nearest zone. Lower values produce more zones."
        ),
    )
    dropoff_spacing_km: float = Field(
        default=0.3,
        description=(
            "Approximate distance in kilometers between drop-off points placed along zone borders. "
            "Smaller values produce more drop-off points per border."
        ),
    )
    dropoff_capacity: int = Field(
        default=20,
        description=(
            "Maximum number of packages a single drop-off point can hold at once. When a box reaches capacity "
            "it is automatically marked full and removed from routing."
        ),
    )


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
    zones: list[ZoneTopologySummary]
    restaurants: list[RestaurantSummary]
    dropoff_points: list[DropoffSummary]
    zone_reasoning: str
