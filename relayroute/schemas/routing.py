"""Routing schemas."""
from pydantic import BaseModel

from relayroute.schemas.order import RelayChainStep


class RoutingRequest(BaseModel):
    city_id: str
    origin: dict
    destination: dict


class EdgeWeight(BaseModel):
    from_zone: str
    to_zone: str
    weight: float
    factors: dict


class RoutingResponse(BaseModel):
    relay_chain: list[RelayChainStep]
    total_handoffs: int
    edge_weights: list[EdgeWeight]
