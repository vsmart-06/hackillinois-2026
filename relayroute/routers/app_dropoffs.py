"""Drop-off points endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_api_key
from relayroute.models import City, DropoffPoint, Order
from relayroute.schemas.common import APIError
from relayroute.schemas.dropoff import (
    DropoffDetailResponse,
    DropoffStatusResponse,
    DropoffStatusUpdate,
    DropoffSummary,
)

router = APIRouter()


@router.get(
    "/dropoffs",
    response_model=list[DropoffSummary],
    summary="List drop-off points for the authenticated city",
    description="Returns all drop-off points in the city from the app API key, including status and capacity fields.",
)
async def list_dropoffs(
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> list[DropoffSummary]:
    dropoffs = db.execute(
        select(DropoffPoint).where(DropoffPoint.city_id == city.id)
    ).scalars().all()
    return [DropoffSummary.model_validate(d) for d in dropoffs]


@router.get(
    "/dropoffs/{dropoff_id}",
    response_model=DropoffDetailResponse,
    summary="Get drop-off point details",
    description="Returns a drop-off point plus active orders currently routed through it.",
    responses={404: {"model": APIError}},
)
async def get_dropoff(
    dropoff_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> DropoffDetailResponse:
    dropoff = db.execute(
        select(DropoffPoint).where(
            DropoffPoint.id == dropoff_id,
            DropoffPoint.city_id == city.id,
        )
    ).scalar_one_or_none()
    if dropoff is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Dropoff {dropoff_id} does not exist"},
        )
    active_orders = db.execute(
        select(Order).where(
            Order.city_id == city.id,
            Order.status.in_(["pending", "in_transit"]),
        )
    ).scalars().all()
    touching_orders = []
    for o in active_orders:
        chain = o.relay_chain or []
        if any(step.get("dropoff_point_id") == dropoff_id for step in chain if isinstance(step, dict)):
            touching_orders.append(o.id)
    return DropoffDetailResponse(
        **DropoffSummary.model_validate(dropoff).model_dump(),
        active_orders=touching_orders,
    )


@router.patch(
    "/dropoffs/{dropoff_id}/status",
    response_model=DropoffStatusResponse,
    summary="Update drop-off status",
    description="Manually sets drop-off status (`active`, `full`, or `disabled`) and returns impacted in-transit order IDs.",
    responses={404: {"model": APIError}},
)
async def update_dropoff_status(
    dropoff_id: str,
    body: DropoffStatusUpdate,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> DropoffStatusResponse:
    dropoff = db.execute(
        select(DropoffPoint).where(
            DropoffPoint.id == dropoff_id,
            DropoffPoint.city_id == city.id,
        )
    ).scalar_one_or_none()
    if dropoff is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Dropoff {dropoff_id} does not exist"},
        )
    dropoff.status = body.status

    affected_orders: list[str] = []
    if body.status in ("full", "disabled"):
        in_transit_orders = db.execute(
            select(Order).where(Order.city_id == city.id, Order.status == "in_transit")
        ).scalars().all()
        for order in in_transit_orders:
            chain = order.relay_chain or []
            if any(step.get("dropoff_point_id") == dropoff_id for step in chain if isinstance(step, dict)):
                affected_orders.append(order.id)

    return DropoffStatusResponse(
        dropoff_id=dropoff.id,
        status=dropoff.status,
        affected_orders=affected_orders,
    )
