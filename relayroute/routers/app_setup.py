"""
POST /app/setup and GET /app/cities. No API key required for setup.
"""
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.models import City, DropoffPoint, Restaurant, Zone
from relayroute.schemas.city import CitySetupRequest, CitySetupResponse
from relayroute.schemas.common import APIError
from relayroute.schemas.dropoff import DropoffSummary
from relayroute.schemas.restaurant import RestaurantSummary
from relayroute.schemas.zone import ZoneSummary
from relayroute.utils import generate_id
from relayroute.services import ai_reasoning, clustering, dropoff_placement, maps

router = APIRouter()


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post(
    "/setup",
    response_model=CitySetupResponse,
    status_code=201,
    summary="Set up a new city",
    responses={
        400: {"description": "Bad request", "model": APIError},
        500: {"description": "Server error", "model": APIError},
    },
)
async def post_setup(
    body: CitySetupRequest,
    db: Session = Depends(get_db),
) -> CitySetupResponse:
    """
    One-time city setup: fetch restaurants, cluster into zones, place drop-offs, generate AI reasoning.
    Takes 5-15 seconds. Returns city_id and full topology. Save the returned api_key for X-API-Key.
    """
    try:
        restaurants_raw = await maps.get_restaurants_in_city(body.city_name)
    except ValueError as e:
        raise HTTPException(status_code=500, detail={"error": "CONFIG_ERROR", "detail": str(e)})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "MAPS_ERROR", "detail": str(e)},
        )
    if not restaurants_raw:
        raise HTTPException(
            status_code=400,
            detail={"error": "NO_RESTAURANTS", "detail": f"No restaurants found for city: {body.city_name}"},
        )
    clusters = clustering.cluster_restaurants(
        restaurants_raw,
        body.epsilon_km,
        body.min_restaurants_per_zone,
    )
    if not clusters:
        raise HTTPException(
            status_code=400,
            detail={"error": "CLUSTERING_FAILED", "detail": "Could not form zones from restaurant data"},
        )
    city_id = generate_id("city")
    api_key_raw = secrets.token_urlsafe(32)
    api_key_hashed = _hash_api_key(api_key_raw)
    now = datetime.now(timezone.utc)
    zone_records: list[Zone] = []
    zone_id_by_index: dict[int, str] = {}
    for i, cluster in enumerate(clusters):
        boundaries = clustering.compute_zone_boundaries(cluster)
        zone_id = generate_id("zone")
        zone_id_by_index[i] = zone_id
        z = Zone(
            id=zone_id,
            city_id=city_id,
            name=f"Zone {i + 1}",
            boundaries=boundaries,
            restaurant_count=len(cluster),
            created_at=now,
        )
        zone_records.append(z)
    zones_for_placement = [
        {
            "id": z.id,
            "name": z.name,
            "boundaries": z.boundaries,
            "restaurant_count": z.restaurant_count,
        }
        for z in zone_records
    ]
    dropoff_placements = dropoff_placement.place_dropoff_points(zones_for_placement, body.dropoff_spacing_km)
    try:
        zone_reasoning = await ai_reasoning.generate_zone_reasoning(body.city_name, zones_for_placement)
    except Exception:
        zone_reasoning = "Zone layout generated from restaurant clustering (DBSCAN)."
    city = City(
        id=city_id,
        name=body.city_name,
        api_key=api_key_hashed,
        epsilon_km=body.epsilon_km,
        min_restaurants_per_zone=body.min_restaurants_per_zone,
        dropoff_spacing_km=body.dropoff_spacing_km,
        dropoff_capacity=body.dropoff_capacity,
        zone_reasoning=zone_reasoning,
        created_at=now,
    )
    db.add(city)
    for z in zone_records:
        db.add(z)
    db.flush()
    restaurant_records: list[Restaurant] = []
    for i, cluster in enumerate(clusters):
        zone_id = zone_id_by_index[i]
        for r in cluster:
            rid = generate_id("restaurant")
            restaurant_records.append(
                Restaurant(
                    id=rid,
                    city_id=city_id,
                    zone_id=zone_id,
                    name=r.get("name", "Restaurant"),
                    lat=r["lat"],
                    lng=r["lng"],
                    address=r.get("address", ""),
                )
            )
    for r in restaurant_records:
        db.add(r)
    db.flush()
    dropoff_records: list[DropoffPoint] = []
    for p in dropoff_placements:
        dp_id = generate_id("dp")
        dropoff_records.append(
            DropoffPoint(
                id=dp_id,
                city_id=city_id,
                zone_id=p["zone_id"],
                lat=p["lat"],
                lng=p["lng"],
                address=f"{p['lat']:.6f}, {p['lng']:.6f}",
                capacity=body.dropoff_capacity,
                current_load=0,
                status="active",
            )
        )
    for d in dropoff_records:
        db.add(d)
    return CitySetupResponse(
        city_id=city_id,
        api_key=api_key_raw,
        zones=[ZoneSummary.model_validate(z) for z in zone_records],
        restaurants=[RestaurantSummary.model_validate(r) for r in restaurant_records],
        dropoff_points=[DropoffSummary.model_validate(d) for d in dropoff_records],
        zone_reasoning=zone_reasoning,
    )


@router.get("/cities", summary="List cities")
async def get_cities(db: Session = Depends(get_db)):
    """List all configured cities (ids and names)."""
    result = db.execute(select(City).order_by(City.created_at.desc()))
    cities = result.scalars().all()
    return [{"id": c.id, "name": c.name} for c in cities]
