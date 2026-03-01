"""Standalone routing endpoint (step 5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_api_key
from relayroute.models import City
from relayroute.models import DropoffPoint, Zone
from relayroute.schemas.common import APIError
from relayroute.schemas.routing import EdgeWeight, RoutingResponse
from relayroute.services import graph, maps

router = APIRouter()


def _point_in_polygon(lat: float, lng: float, polygon: dict) -> bool:
    coords = (polygon or {}).get("coordinates", [[]])
    if not coords or not coords[0]:
        return False
    ring = coords[0]
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _zone_centroid(zone: Zone) -> tuple[float, float]:
    coords = (zone.boundaries or {}).get("coordinates", [[]])
    if not coords or not coords[0]:
        return (0.0, 0.0)
    ring = coords[0]
    lat = sum(p[1] for p in ring) / len(ring)
    lng = sum(p[0] for p in ring) / len(ring)
    return (lat, lng)


def _resolve_zone_by_point(zones: list[Zone], lat: float, lng: float) -> Zone:
    containing = [z for z in zones if _point_in_polygon(lat, lng, z.boundaries)]
    if containing:
        return min(
            containing,
            key=lambda z: (lat - _zone_centroid(z)[0]) ** 2 + (lng - _zone_centroid(z)[1]) ** 2,
        )
    return min(
        zones,
        key=lambda z: (lat - _zone_centroid(z)[0]) ** 2 + (lng - _zone_centroid(z)[1]) ** 2,
    )


@router.get(
    "/path",
    response_model=RoutingResponse,
    summary="Inspect computed routing path",
    description="Computes relay path between origin and destination coordinates using the authenticated city's current zone graph.",
    responses={400: {"model": APIError}, 404: {"model": APIError}},
)
async def get_routing_path(
    origin_lat: float = Query(...),
    origin_lng: float = Query(...),
    destination_lat: float = Query(...),
    destination_lng: float = Query(...),
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> RoutingResponse:
    zones = db.execute(select(Zone).where(Zone.city_id == city.id)).scalars().all()
    if not zones:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"No zones configured for city {city.id}"},
        )
    dropoffs = db.execute(
        select(DropoffPoint).where(
            DropoffPoint.city_id == city.id,
            DropoffPoint.status == "active",
        )
    ).scalars().all()

    origin_zone = _resolve_zone_by_point(zones, float(origin_lat), float(origin_lng))
    destination_zone = _resolve_zone_by_point(zones, float(destination_lat), float(destination_lng))

    # Same-zone routes are direct destination deliveries (no relay handoff path).
    if origin_zone.id == destination_zone.id:
        return RoutingResponse(
            relay_chain=[],
            total_handoffs=0,
            edge_weights=[],
        )

    travel_times: dict[tuple[str, str], float] = {}
    for z1 in zones:
        for z2 in zones:
            if z1.id == z2.id:
                continue
            c1 = _zone_centroid(z1)
            c2 = _zone_centroid(z2)
            travel_times[(z1.id, z2.id)] = await maps.get_travel_time(c1, c2)

    routing_graph = graph.build_graph(zones=zones, dropoff_points=dropoffs, travel_times=travel_times)
    try:
        path, _ = graph.dijkstra(routing_graph, origin_zone.id, destination_zone.id)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "ROUTING_FAILED", "detail": str(exc)},
        ) from exc

    try:
        relay_chain = graph.path_to_relay_chain(
            path=path,
            zones={z.id: z for z in zones},
            dropoffs={d.id: d for d in dropoffs},
            destination_lat=destination_lat,
            destination_lng=destination_lng,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "ROUTING_FAILED", "detail": str(exc)},
        ) from exc

    edge_weights: list[EdgeWeight] = []
    for i in range(len(path) - 1):
        z_from = path[i]
        z_to = path[i + 1]
        w = float(travel_times.get((z_from, z_to), 999.0))
        edge_weights.append(
            EdgeWeight(
                from_zone=z_from,
                to_zone=z_to,
                weight=w,
                factors={
                    "traffic": w,
                    "capacity_penalty": 0.0,
                    "partner_availability_penalty": 0.0,
                },
            )
        )

    return RoutingResponse(
        relay_chain=relay_chain,
        total_handoffs=max(0, len(relay_chain) - 1),
        edge_weights=edge_weights,
    )
