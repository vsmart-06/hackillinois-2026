"""Routing schemas."""
from pydantic import BaseModel, ConfigDict

from relayroute.schemas.order import Coordinates, RelayChainStep


class RoutingRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates


class EdgeWeightFactors(BaseModel):
    traffic: float
    capacity_penalty: float
    partner_availability_penalty: float


class EdgeWeight(BaseModel):
    from_zone: str
    to_zone: str
    weight: float
    factors: EdgeWeightFactors


class RoutingResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "relay_chain": [
                    {
                        "zone_id": "zone_bandra_west_02",
                        "dropoff_point_id": "dp_mum_khar_11",
                        "coords": {"lat": 19.0714, "lng": 72.8361},
                    },
                    {
                        "zone_id": "zone_andheri_east_03",
                        "dropoff_point_id": "dp_mum_saki_07",
                        "coords": {"lat": 19.1087, "lng": 72.8899},
                    },
                ],
                "total_handoffs": 1,
                "edge_weights": [
                    {
                        "from_zone": "zone_bandra_west_02",
                        "to_zone": "zone_andheri_east_03",
                        "weight": 18.6,
                        "factors": {
                            "traffic": 13.2,
                            "capacity_penalty": 3.1,
                            "partner_availability_penalty": 2.3,
                        },
                    }
                ],
            }
        }
    )

    relay_chain: list[RelayChainStep]
    total_handoffs: int
    edge_weights: list[EdgeWeight]
