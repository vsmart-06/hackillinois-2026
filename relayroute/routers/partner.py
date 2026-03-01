"""Partner endpoints (step 4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_partner_api_key
from relayroute.models import Order, Partner, TaskEvent
from relayroute.schemas.common import APIError
from relayroute.schemas.partner import (
    CompleteTaskRequest,
    CompleteTaskResponse,
    NextTaskResponse,
    PartnerProfileResponse,
    PartnerStatusUpdate,
)
from relayroute.services import relay

router = APIRouter()
task_router = APIRouter()


@router.get(
    "",
    response_model=PartnerProfileResponse,
    responses={404: {"model": APIError}},
)
async def get_partner_profile(
    partner: Partner = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
) -> PartnerProfileResponse:
    current_task = None
    if partner.current_order_id:
        order = db.execute(select(Order).where(Order.id == partner.current_order_id)).scalar_one_or_none()
        if order is not None:
            current_task = {
                "order_id": order.id,
                "destination": order.current_dropoff_id,
            }
    return PartnerProfileResponse(
        partner_id=partner.id,
        name=partner.name,
        zone_id=partner.zone_id,
        status=partner.status,
        current_task=current_task,
    )


@router.patch(
    "/status",
    responses={404: {"model": APIError}},
)
async def update_partner_status(
    body: PartnerStatusUpdate,
    partner: Partner = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
):
    partner.status = body.status
    if body.status != "carrying":
        partner.current_order_id = None
    return {"partner_id": partner.id, "status": partner.status}


@task_router.get(
    "/next-task",
    response_model=NextTaskResponse,
    responses={404: {"model": APIError}},
)
async def get_next_task(
    partner: Partner = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
) -> NextTaskResponse:
    task = await relay.get_next_task(partner_id=partner.id, db=db)
    return NextTaskResponse(partner_id=partner.id, task=task)


@task_router.post(
    "/complete-task",
    response_model=CompleteTaskResponse,
    responses={404: {"model": APIError}, 400: {"model": APIError}},
)
async def complete_task(
    body: CompleteTaskRequest,
    partner: Partner = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
) -> CompleteTaskResponse:
    if body.city_id and partner.city_id != body.city_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Partner {partner.id} does not belong to city {body.city_id}"},
        )
    completed_dropoff_id = body.completed_dropoff_id or body.dropoff_point_id
    if not completed_dropoff_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "BAD_REQUEST", "detail": "Either completed_dropoff_id or dropoff_point_id is required"},
        )
    try:
        result = await relay.advance_relay(
            order_id=body.order_id,
            completed_dropoff_id=completed_dropoff_id,
            partner_id=partner.id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "BAD_REQUEST", "detail": str(exc)},
        ) from exc
    return CompleteTaskResponse(
        partner_id=partner.id,
        order_id=body.order_id,
        order_status=result["order_status"],
        dropoff_status=result["dropoff_status"],
        next_partner_id=result.get("next_partner_id"),
    )


@task_router.get(
    "/task-history",
    responses={404: {"model": APIError}},
)
async def get_task_history(
    partner: Partner = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
):
    events = db.execute(
        select(TaskEvent).where(TaskEvent.partner_id == partner.id).order_by(TaskEvent.timestamp.desc())
    ).scalars().all()
    return {
        "partner_id": partner.id,
        "tasks": [
            {
                "order_id": e.order_id,
                "task_type": e.event,
                "completed_at": e.timestamp,
                "dropoff_id": e.dropoff_id,
            }
            for e in events
        ],
    }
