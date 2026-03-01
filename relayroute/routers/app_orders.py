"""Orders endpoints (step 3)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.middleware.auth import verify_api_key
from relayroute.models import City, DropoffPoint, Order, Restaurant, Zone
from relayroute.schemas.common import APIError
from relayroute.schemas.order import OrderRequest, OrderResponse, OrderStatusResponse
from relayroute.services import graph, maps, relay
from relayroute.utils import generate_id

router = APIRouter()


def _point_in_polygon(lat: float, lng: float, polygon: dict) -> bool:
    """Ray-casting point-in-polygon for GeoJSON polygon coordinates."""
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


@router.post(
    "/orders",
    response_model=OrderResponse,
    responses={
        400: {"model": APIError},
        401: {"model": APIError},
        404: {"model": APIError},
        500: {"model": APIError},
    },
)
async def create_order(
    body: OrderRequest,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> OrderResponse:
    if body.city_id != city.id:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "detail": "API key does not match requested city_id"},
        )

    restaurant = db.execute(
        select(Restaurant).where(
            Restaurant.id == body.restaurant_id,
            Restaurant.city_id == body.city_id,
        )
    ).scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Restaurant {body.restaurant_id} does not exist"},
        )

    try:
        destination = await maps.geocode_address(body.delivery_address)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "GEOCODE_FAILED", "detail": str(exc)},
        ) from exc

    zones = db.execute(select(Zone).where(Zone.city_id == body.city_id)).scalars().all()
    if not zones:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"No zones configured for city {body.city_id}"},
        )

    origin_zone = next((z for z in zones if z.id == restaurant.zone_id), None)
    if origin_zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": "Restaurant zone not found"},
        )

    destination_zone = None
    for z in zones:
        if _point_in_polygon(destination["lat"], destination["lng"], z.boundaries):
            destination_zone = z
            break
    if destination_zone is None:
        # Fallback to nearest zone centroid
        destination_zone = min(
            zones,
            key=lambda z: (destination["lat"] - _zone_centroid(z)[0]) ** 2
            + (destination["lng"] - _zone_centroid(z)[1]) ** 2,
        )

    dropoffs = db.execute(
        select(DropoffPoint).where(
            DropoffPoint.city_id == body.city_id,
            DropoffPoint.status == "active",
        )
    ).scalars().all()

    # Travel times between zone centroids.
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

    relay_chain = graph.path_to_relay_chain(
        path=path,
        zones={z.id: z for z in zones},
        dropoffs={d.id: d for d in dropoffs},
    )
    estimated_handoffs = max(0, len(relay_chain) - 1)

    order = Order(
        id=generate_id("ord"),
        city_id=body.city_id,
        restaurant_id=body.restaurant_id,
        delivery_address=body.delivery_address,
        delivery_lat=destination["lat"],
        delivery_lng=destination["lng"],
        status="pending",
        relay_chain=relay_chain,
        current_dropoff_id=relay_chain[0]["dropoff_point_id"] if relay_chain else None,
        current_zone_id=origin_zone.id,
        estimated_handoffs=estimated_handoffs,
        remaining_handoffs=estimated_handoffs,
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    await relay.initialize_relay(order, db)
    db.flush()

    return OrderResponse(
        order_id=order.id,
        relay_chain=relay_chain,
        estimated_handoffs=estimated_handoffs,
    )


@router.get("/orders")
async def list_orders(
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    orders = db.execute(
        select(Order).where(Order.city_id == city.id).order_by(Order.created_at.desc())
    ).scalars().all()
    return [
        {
            "order_id": o.id,
            "restaurant_id": o.restaurant_id,
            "status": o.status,
            "estimated_handoffs": o.estimated_handoffs,
            "remaining_handoffs": o.remaining_handoffs,
            "created_at": o.created_at,
        }
        for o in orders
    ]


@router.get(
    "/orders/{order_id}",
    responses={404: {"model": APIError}},
)
async def get_order(
    order_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    order = db.execute(
        select(Order).where(Order.id == order_id, Order.city_id == city.id)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Order {order_id} does not exist"},
        )
    return {
        "order_id": order.id,
        "city_id": order.city_id,
        "restaurant_id": order.restaurant_id,
        "delivery_address": order.delivery_address,
        "delivery_lat": order.delivery_lat,
        "delivery_lng": order.delivery_lng,
        "status": order.status,
        "relay_chain": order.relay_chain,
        "current_dropoff_id": order.current_dropoff_id,
        "current_zone_id": order.current_zone_id,
        "estimated_handoffs": order.estimated_handoffs,
        "remaining_handoffs": order.remaining_handoffs,
        "created_at": order.created_at,
    }


@router.get(
    "/orders/{order_id}/status",
    response_model=OrderStatusResponse,
    responses={404: {"model": APIError}},
)
async def get_order_status(
    order_id: str,
    city: City = Depends(verify_api_key),
    db: Session = Depends(get_db),
) -> OrderStatusResponse:
    order = db.execute(
        select(Order).where(Order.id == order_id, Order.city_id == city.id)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Order {order_id} does not exist"},
        )
    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
        remaining_handoffs=order.remaining_handoffs,
        current_zone_id=order.current_zone_id,
        current_dropoff_id=order.current_dropoff_id,
    )
