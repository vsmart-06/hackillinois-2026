"""Partner schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from relayroute.schemas.order import Coordinates


class PartnerStatusUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "available",
            }
        }
    )

    status: Literal["available", "carrying", "offline"]


class PartnerRegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Rohan Patil",
                "phone": "+91-9000000001",
                "zone_id": "zone_bandra_west_02",
                "city_id": "city_mumbai_demo01",
            }
        }
    )

    name: str
    phone: str
    zone_id: str = Field(
        description=(
            "The zone this partner will operate in. Partners only receive tasks within their assigned zone "
            "and should not cross zone boundaries."
        )
    )
    city_id: str = Field(
        description="Must match the city associated with the app API key used during setup."
    )


class PartnerZoneInfo(BaseModel):
    id: str
    boundaries: dict
    dropoff_points: list[dict]


class PartnerRegisterResponse(BaseModel):
    partner_id: str
    api_key: str
    zone: PartnerZoneInfo


class CompleteTaskRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_id": "ord_mum_7f3d9c10",
                "dropoff_point_id": "dp_mum_khar_11",
            }
        }
    )

    order_id: str
    dropoff_point_id: str


class NextTaskResponse(BaseModel):
    partner_id: str
    task: PartnerTask | None = Field(
        description=(
            "The partner's current task. Returns null if no task is currently assigned and the partner should "
            "remain on standby."
        )
    )


class CompleteTaskResponse(BaseModel):
    partner_id: str
    order_id: str
    order_status: str
    dropoff_status: str
    next_partner_id: str | None = None


class PartnerProfileResponse(BaseModel):
    partner_id: str
    name: str
    zone_id: str
    status: str
    current_task: PartnerCurrentTask | None = None


class PartnerCurrentTask(BaseModel):
    order_id: str
    destination: str | None


class PartnerTask(BaseModel):
    task_type: str = Field(
        description=(
            "The action the partner must perform. pickup_restaurant means collect from the originating restaurant. "
            "pickup_dropoff means collect from a drop-off box. deliver_dropoff means deposit at the next drop-off box "
            "in the relay chain. deliver_destination means directly deliver to the final customer destination."
        )
    )
    instructions: str = Field(
        description="Human-readable instruction string suitable for display in a partner mobile app."
    )
    order_id: str
    dropoff_id: str | None
    zone_id: str | None
    coords: Coordinates | None


class PartnerTaskHistoryItem(BaseModel):
    order_id: str
    task_type: str
    completed_at: datetime
    dropoff_id: str | None


class PartnerTaskHistoryResponse(BaseModel):
    partner_id: str
    tasks: list[PartnerTaskHistoryItem]


class PartnerStatusResponse(BaseModel):
    partner_id: str
    status: str
