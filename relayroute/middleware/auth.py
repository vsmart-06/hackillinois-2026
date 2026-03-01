"""X-API-Key verification dependency for /app routes."""
import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.database import get_db
from relayroute.models import City


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> City:
    """
    Verify X-API-Key against stored hashed city api_key.
    Returns matched City object or raises 401.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "detail": "Missing API key"},
        )

    hashed = _hash_api_key(x_api_key)
    city = db.execute(select(City).where(City.api_key == hashed)).scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "detail": "Missing or invalid API key"},
        )
    return city
