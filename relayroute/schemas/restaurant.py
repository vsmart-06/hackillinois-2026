"""Restaurant schemas."""
from pydantic import BaseModel, ConfigDict


class RestaurantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city_id: str
    zone_id: str
    name: str
    lat: float
    lng: float
    address: str
