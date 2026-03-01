"""Routing schemas."""
from pydantic import BaseModel, ConfigDict, Field

from relayroute.schemas.order import Coordinates, RelayChainStep


class RoutingRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates


class EdgeWeightFactors(BaseModel):
    traffic: float = Field(
        description=(
            "Estimated travel time in minutes between zone centroids, sourced from Google Maps Distance Matrix API in real time."
        )
    )
    capacity_penalty: float = Field(
        description=(
            "Additional weight applied when a drop-off point along this edge is near capacity. "
            "Increases as load approaches the capacity ceiling."
        )
    )
    partner_availability_penalty: float = Field(
        description=(
            "Additional weight applied when the destination zone has no available partners. "
            "Penalizes routing through zones that cannot accept a handoff."
        )
    )


class EdgeWeight(BaseModel):
    from_zone: str
    to_zone: str
    weight: float = Field(description="Composite edge weight used by Dijkstra's algorithm. Lower is better.")
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
