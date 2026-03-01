"""Partner schemas."""
from typing import Literal

from pydantic import BaseModel


class PartnerStatusUpdate(BaseModel):
    status: Literal["available", "carrying", "offline"]


class PartnerRegisterRequest(BaseModel):
    name: str
    phone: str
    zone_id: str
    city_id: str


class PartnerRegisterResponse(BaseModel):
    partner_id: str
    api_key: str
    zone: dict


class CompleteTaskRequest(BaseModel):
    city_id: str | None = None
    order_id: str
    completed_dropoff_id: str | None = None
    dropoff_point_id: str | None = None


class NextTaskResponse(BaseModel):
    partner_id: str
    task: dict | None


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
    current_task: dict | None = None
