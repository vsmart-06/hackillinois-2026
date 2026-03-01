"""
Google Maps API calls. All use httpx.AsyncClient.
"""
from __future__ import annotations

import asyncio
import httpx

from relayroute.config import get_settings


async def get_restaurants_in_city(city_name: str) -> list[dict]:
    """
    Use Google Maps Places API (Text Search) to fetch restaurants in the city.
    Paginate using next_page_token until exhausted.
    Return list of {name, lat, lng, address, place_id}.
    """
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY (or GOOGLE_API_KEY) is not set")
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    results: list[dict] = []
    page_token: str | None = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params: dict = {
                "query": f"restaurants in {city_name}",
                "key": settings.google_maps_api_key,
            }
            if page_token:
                params["pagetoken"] = page_token
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                raise RuntimeError(f"Places API error: {data.get('status')} - {data.get('error_message', '')}")
            for item in data.get("results", []):
                geometry = item.get("geometry", {})
                location = geometry.get("location", {})
                results.append({
                    "name": item.get("name", ""),
                    "lat": location.get("lat"),
                    "lng": location.get("lng"),
                    "address": item.get("formatted_address", ""),
                    "place_id": item.get("place_id", ""),
                })
            page_token = data.get("next_page_token")
            if not page_token:
                break
            await asyncio.sleep(2)
    return [r for r in results if r.get("lat") is not None and r.get("lng") is not None]


async def get_travel_time(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """
    Use Google Maps Distance Matrix API for travel time in minutes between (lat, lng) coordinates.
    """
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set")
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin[0]},{origin[1]}",
        "destinations": f"{destination[0]},{destination[1]}",
        "key": settings.google_maps_api_key,
        "mode": "driving",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "OK":
        return 999.0
    rows = data.get("rows", [])
    if not rows or not rows[0].get("elements"):
        return 999.0
    elem = rows[0]["elements"][0]
    if elem.get("status") != "OK":
        return 999.0
    duration = elem.get("duration", {}).get("value")
    if duration is None:
        return 999.0
    return duration / 60.0


async def geocode_address(address: str) -> dict:
    """Convert a delivery address string to {lat, lng} using Geocoding API."""
    settings = get_settings()
    if not settings.google_maps_api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set")
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": settings.google_maps_api_key}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocoding failed for address: {address}")
    loc = data["results"][0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"]}
