"""Partner endpoints (step 4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.models import Partner
from relayroute.schemas.common import APIError
from relayroute.schemas.partner import (
    CompleteTaskRequest,
    CompleteTaskResponse,
    NextTaskResponse,
)
from relayroute.services import relay

router = APIRouter()


@router.get(
    "/{partner_id}/next-task",
    response_model=NextTaskResponse,
    responses={404: {"model": APIError}},
)
async def get_next_task(
    partner_id: str,
    city_id: str,
    db: Session = Depends(get_db),
) -> NextTaskResponse:
    partner = db.execute(
        select(Partner).where(Partner.id == partner_id)
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Partner {partner_id} does not exist"},
        )
    if partner.city_id != city_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Partner {partner_id} does not belong to city {city_id}"},
        )
    task = await relay.get_next_task(partner_id=partner_id, db=db)
    return NextTaskResponse(partner_id=partner_id, task=task)


@router.post(
    "/{partner_id}/complete-task",
    response_model=CompleteTaskResponse,
    responses={404: {"model": APIError}, 400: {"model": APIError}},
)
async def complete_task(
    partner_id: str,
    body: CompleteTaskRequest,
    db: Session = Depends(get_db),
) -> CompleteTaskResponse:
    partner = db.execute(
        select(Partner).where(Partner.id == partner_id)
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Partner {partner_id} does not exist"},
        )
    if partner.city_id != body.city_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Partner {partner_id} does not belong to city {body.city_id}"},
        )
    try:
        result = await relay.advance_relay(
            order_id=body.order_id,
            completed_dropoff_id=body.completed_dropoff_id,
            partner_id=partner_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "BAD_REQUEST", "detail": str(exc)},
        ) from exc
    return CompleteTaskResponse(
        partner_id=partner_id,
        order_id=body.order_id,
        order_status=result["order_status"],
        dropoff_status=result["dropoff_status"],
        next_partner_id=result.get("next_partner_id"),
    )
