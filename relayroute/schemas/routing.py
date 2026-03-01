"""Routing schemas."""
from pydantic import BaseModel

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
    relay_chain: list[RelayChainStep]
    total_handoffs: int
    edge_weights: list[EdgeWeight]
