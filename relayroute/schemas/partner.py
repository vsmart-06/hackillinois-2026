"""Partner schemas."""
from typing import Literal

from pydantic import BaseModel


class PartnerStatusUpdate(BaseModel):
    status: Literal["available", "carrying", "offline"]


class CompleteTaskRequest(BaseModel):
    city_id: str
    order_id: str
    completed_dropoff_id: str


class NextTaskResponse(BaseModel):
    partner_id: str
    task: dict | None


class CompleteTaskResponse(BaseModel):
    partner_id: str
    order_id: str
    order_status: str
    dropoff_status: str
    next_partner_id: str | None = None
