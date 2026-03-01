"""App-facing partner management endpoints."""
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.models import Partner, Zone
from relayroute.schemas.common import APIError
from relayroute.schemas.partner import PartnerRegisterRequest, PartnerRegisterResponse
from relayroute.utils import generate_id

router = APIRouter()


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post(
    "/register",
    response_model=PartnerRegisterResponse,
    responses={404: {"model": APIError}},
)
async def register_partner(
    body: PartnerRegisterRequest,
    db: Session = Depends(get_db),
) -> PartnerRegisterResponse:
    zone = db.execute(
        select(Zone).where(Zone.id == body.zone_id, Zone.city_id == body.city_id)
    ).scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "detail": f"Zone {body.zone_id} does not exist in city {body.city_id}"},
        )
    partner_api_key = secrets.token_urlsafe(32)
    partner = Partner(
        id=generate_id("p"),
        city_id=body.city_id,
        zone_id=body.zone_id,
        api_key=_hash_api_key(partner_api_key),
        name=body.name,
        phone=body.phone,
        status="available",
        current_order_id=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(partner)
    db.flush()
    return PartnerRegisterResponse(
        partner_id=partner.id,
        api_key=partner_api_key,
        zone={"id": zone.id, "boundaries": zone.boundaries, "dropoff_points": []},
    )
