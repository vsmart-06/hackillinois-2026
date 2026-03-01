"""Partner schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from relayroute.schemas.order import Coordinates


class PartnerStatusUpdate(BaseModel):
    status: Literal["available", "carrying", "offline"]


class PartnerRegisterRequest(BaseModel):
    name: str
    phone: str
    zone_id: str
    city_id: str


class PartnerZoneInfo(BaseModel):
    id: str
    boundaries: dict
    dropoff_points: list[dict]


class PartnerRegisterResponse(BaseModel):
    partner_id: str
    api_key: str
    zone: PartnerZoneInfo


class CompleteTaskRequest(BaseModel):
    order_id: str
    dropoff_point_id: str


class NextTaskResponse(BaseModel):
    partner_id: str
    task: PartnerTask | None


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
    task_type: str
    instructions: str
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
