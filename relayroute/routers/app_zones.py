"""Zones endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_api_key
from relayroute.models import City, DropoffPoint, Order, Partner, Zone
from relayroute.schemas.common import APIError
from relayroute.schemas.zone import ZoneLoadResponse, ZoneSummary

router = APIRouter()


@router.get("/zones")
async def list_zones(
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> list[ZoneSummary]:
    zones = db.execute(
        select(Zone).where(Zone.city_id == city.id).order_by(Zone.created_at.asc())
    ).scalars().all()
    return [ZoneSummary.model_validate(z) for z in zones]


@router.get(
    "/zones/{zone_id}",
    response_model=ZoneSummary,
    responses={404: {"model": APIError}},
)
async def get_zone(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZoneSummary:
    zone = db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)
    ).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )
    return ZoneSummary.model_validate(zone)


@router.get(
    "/zones/{zone_id}/load",
    response_model=ZoneLoadResponse,
    responses={404: {"model": APIError}},
)
async def get_zone_load(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZoneLoadResponse:
    zone = db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)
    ).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )

    dropoffs = db.execute(
        select(DropoffPoint).where(
            DropoffPoint.city_id == city.id,
            DropoffPoint.zone_id == zone_id,
        )
    ).scalars().all()
    partners = db.execute(
        select(Partner).where(
            Partner.city_id == city.id,
            Partner.zone_id == zone_id,
        )
    ).scalars().all()
    orders = db.execute(
        select(Order).where(
            Order.city_id == city.id,
            Order.current_zone_id == zone_id,
        )
    ).scalars().all()

    total_capacity = sum(d.capacity for d in dropoffs)
    current_load = sum(d.current_load for d in dropoffs)
    utilization = (current_load / total_capacity) if total_capacity > 0 else 0.0

    return ZoneLoadResponse(
        zone_id=zone_id,
        city_id=city.id,
        dropoff_count=len(dropoffs),
        active_dropoffs=sum(1 for d in dropoffs if d.status == "active"),
        full_dropoffs=sum(1 for d in dropoffs if d.status == "full"),
        disabled_dropoffs=sum(1 for d in dropoffs if d.status == "disabled"),
        total_capacity=total_capacity,
        current_load=current_load,
        utilization_ratio=round(utilization, 4),
        partners_available=sum(1 for p in partners if p.status == "available"),
        partners_carrying=sum(1 for p in partners if p.status == "carrying"),
        partners_offline=sum(1 for p in partners if p.status == "offline"),
        orders_pending=sum(1 for o in orders if o.status == "pending"),
        orders_in_transit=sum(1 for o in orders if o.status == "in_transit"),
        orders_delivered=sum(1 for o in orders if o.status == "delivered"),
    )


@router.get("/zones/load/summary")
async def get_city_load_summary(
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """City-wide load snapshot across zones."""
    zones = db.execute(select(Zone).where(Zone.city_id == city.id)).scalars().all()
    zone_loads: list[ZoneLoadResponse] = []
    for z in zones:
        zone_loads.append(await get_zone_load(z.id, city=city, db=db))
    return {
        "city_id": city.id,
        "zone_count": len(zone_loads),
        "zones": [zl.model_dump() for zl in zone_loads],
        "avg_utilization_ratio": round(
            (sum(zl.utilization_ratio for zl in zone_loads) / len(zone_loads)) if zone_loads else 0.0,
            4,
        ),
    }
