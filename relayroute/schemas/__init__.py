"""Pydantic request/response schemas."""
from relayroute.schemas.common import APIError
from relayroute.schemas.city import CitySetupRequest, CitySetupResponse
from relayroute.schemas.order import OrderRequest, OrderResponse, OrderStatusResponse, RelayChainStep
from relayroute.schemas.partner import (
    CompleteTaskRequest,
    CompleteTaskResponse,
    NextTaskResponse,
    PartnerProfileResponse,
    PartnerRegisterRequest,
    PartnerRegisterResponse,
    PartnerStatusUpdate,
)
from relayroute.schemas.routing import EdgeWeight, RoutingRequest, RoutingResponse
from relayroute.schemas.zone import ZoneLoadResponse, ZoneSummary
from relayroute.schemas.restaurant import RestaurantSummary
from relayroute.schemas.dropoff import DropoffDetailResponse, DropoffStatusResponse, DropoffStatusUpdate, DropoffSummary

__all__ = [
    "APIError",
    "CitySetupRequest",
    "CitySetupResponse",
    "OrderRequest",
    "OrderResponse",
    "OrderStatusResponse",
    "RelayChainStep",
    "PartnerStatusUpdate",
    "PartnerRegisterRequest",
    "PartnerRegisterResponse",
    "PartnerProfileResponse",
    "CompleteTaskRequest",
    "NextTaskResponse",
    "CompleteTaskResponse",
    "RoutingRequest",
    "EdgeWeight",
    "RoutingResponse",
    "DropoffDetailResponse",
    "DropoffStatusUpdate",
    "DropoffStatusResponse",
    "ZoneSummary",
    "ZoneLoadResponse",
    "RestaurantSummary",
    "DropoffSummary",
]
