"""Zones endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_api_key
from relayroute.models import City, DropoffPoint, Order, Partner, Restaurant, Zone
from relayroute.schemas.common import APIError
from relayroute.schemas.zone import (
    ZoneDetailResponse,
    ZoneDropoffsResponse,
    ZoneLoadResponse,
    ZoneOrdersResponse,
    ZonePartnersResponse,
    ZoneSummary,
)

router = APIRouter()


@router.get(
    "/zones",
    response_model=list[ZoneSummary],
    summary="List zones for the authenticated city",
    description="Returns all zones configured for the city resolved from the app API key.",
)
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
    response_model=ZoneDetailResponse,
    summary="Get full zone details",
    description="Returns zone boundaries and live resources in the zone, including restaurants, drop-off points, active partners, and active orders.",
    responses={404: {"model": APIError}},
)
async def get_zone(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZoneDetailResponse:
    zone = db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)
    ).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )

    restaurants = db.execute(
        select(Restaurant).where(Restaurant.city_id == city.id, Restaurant.zone_id == zone_id)
    ).scalars().all()
    dropoffs = db.execute(
        select(DropoffPoint).where(DropoffPoint.city_id == city.id, DropoffPoint.zone_id == zone_id)
    ).scalars().all()
    partners = db.execute(
        select(Partner).where(Partner.city_id == city.id, Partner.zone_id == zone_id)
    ).scalars().all()
    orders = db.execute(
        select(Order).where(Order.city_id == city.id, Order.current_zone_id == zone_id)
    ).scalars().all()
    return ZoneDetailResponse(
        zone_id=zone.id,
        city_id=zone.city_id,
        name=zone.name,
        boundaries=zone.boundaries,
        restaurant_count=zone.restaurant_count,
        restaurants=[{"id": r.id, "name": r.name, "lat": r.lat, "lng": r.lng} for r in restaurants],
        dropoff_points=[{"id": d.id, "status": d.status, "current_load": d.current_load, "capacity": d.capacity} for d in dropoffs],
        active_partners=[{"partner_id": p.id, "name": p.name, "status": p.status} for p in partners],
        active_orders=[{"order_id": o.id, "status": o.status} for o in orders if o.status in ("pending", "in_transit")],
    )


@router.get(
    "/zones/{zone_id}/partners",
    response_model=ZonePartnersResponse,
    summary="List partners assigned to a zone",
    description="Returns all partners currently mapped to the specified zone and their real-time availability status.",
    responses={404: {"model": APIError}},
)
async def get_zone_partners(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZonePartnersResponse:
    zone = db.execute(select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )
    partners = db.execute(
        select(Partner).where(Partner.city_id == city.id, Partner.zone_id == zone_id)
    ).scalars().all()
    return ZonePartnersResponse(
        zone_id=zone_id,
        partners=[{"partner_id": p.id, "name": p.name, "status": p.status} for p in partners],
    )


@router.get(
    "/zones/{zone_id}/dropoffs",
    response_model=ZoneDropoffsResponse,
    summary="List zone drop-off points",
    description="Returns all drop-off points in a zone with their current load and status.",
    responses={404: {"model": APIError}},
)
async def get_zone_dropoffs(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZoneDropoffsResponse:
    zone = db.execute(select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )
    dropoffs = db.execute(
        select(DropoffPoint).where(DropoffPoint.city_id == city.id, DropoffPoint.zone_id == zone_id)
    ).scalars().all()
    return ZoneDropoffsResponse(
        zone_id=zone_id,
        dropoff_points=[
            {
                "dropoff_id": d.id,
                "status": d.status,
                "current_load": d.current_load,
                "capacity": d.capacity,
                "lat": d.lat,
                "lng": d.lng,
            }
            for d in dropoffs
        ],
    )


@router.get(
    "/zones/{zone_id}/orders",
    response_model=ZoneOrdersResponse,
    summary="List active orders in a zone",
    description="Returns active orders currently traversing the specified zone.",
    responses={404: {"model": APIError}},
)
async def get_zone_orders(
    zone_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> ZoneOrdersResponse:
    zone = db.execute(
        select(Zone).where(Zone.id == zone_id, Zone.city_id == city.id)
    ).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {zone_id} does not exist"},
        )
    orders = db.execute(
        select(Order).where(
            Order.city_id == city.id,
            Order.current_zone_id == zone_id,
            Order.status.in_(["pending", "in_transit"]),
        )
    ).scalars().all()
    return ZoneOrdersResponse(
        zone_id=zone_id,
        orders=[
            {
                "order_id": o.id,
                "status": o.status,
                "current_dropoff_id": o.current_dropoff_id,
                "remaining_handoffs": o.remaining_handoffs,
            }
            for o in orders
        ],
    )


@router.get(
    "/zones/{zone_id}/load",
    response_model=ZoneLoadResponse,
    summary="Get zone load analytics",
    description="Returns live utilization and capacity metrics for the zone, including drop-off, partner, and order counters.",
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


