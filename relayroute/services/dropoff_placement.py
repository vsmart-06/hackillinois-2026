"""
Drop-off point placement sampled inside zone polygons.
"""
from __future__ import annotations

import math
import random


def _centroid(zone: dict) -> tuple[float, float]:
    boundaries = zone.get("boundaries") or {}
    coords = boundaries.get("coordinates", [[]])
    if not coords or not coords[0]:
        return (float(zone.get("lat", 0.0)), float(zone.get("lng", 0.0)))
    ring = coords[0]
    lats = [float(p[1]) for p in ring]
    lngs = [float(p[0]) for p in ring]
    return (sum(lats) / len(lats), sum(lngs) / len(lngs))


def _ring(zone: dict) -> list[tuple[float, float]]:
    boundaries = zone.get("boundaries") or {}
    coords = boundaries.get("coordinates", [[]])
    if not coords or not coords[0]:
        return []
    ring = coords[0]
    return [(float(p[1]), float(p[0])) for p in ring if len(p) >= 2]


def _point_in_polygon(lat: float, lng: float, polygon_lat_lng: list[tuple[float, float]]) -> bool:
    if len(polygon_lat_lng) < 3:
        return False
    inside = False
    j = len(polygon_lat_lng) - 1
    for i in range(len(polygon_lat_lng)):
        yi, xi = polygon_lat_lng[i]
        yj, xj = polygon_lat_lng[j]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _bbox_lat_lng(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    return (min(lats), max(lats), min(lngs), max(lngs))


def _polygon_area_km2(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    # Shoelace area in degrees^2 then rough conversion to km^2.
    area = 0.0
    for i in range(len(points)):
        lat1, lng1 = points[i]
        lat2, lng2 = points[(i + 1) % len(points)]
        area += lng1 * lat2 - lng2 * lat1
    deg2 = abs(area) / 2.0
    return deg2 * (111.0 * 111.0)


def _dedupe(points: list[dict]) -> list[dict]:
    seen: set[tuple[str, int, int]] = set()
    out: list[dict] = []
    for p in points:
        key = (str(p["zone_id"]), int(round(float(p["lat"]) * 1e5)), int(round(float(p["lng"]) * 1e5)))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def place_dropoff_points(
    zones: list[dict],
    spacing_km: float,
) -> list[dict]:
    """
    Place drop-off points randomly inside each zone polygon.
    Also place one at each zone centroid as fallback.
    Return list of {lat, lng, zone_id}.
    """
    result: list[dict] = []
    for z in zones:
        zone_id = z["id"]
        c_lat, c_lng = _centroid(z)
        result.append({"lat": float(c_lat), "lng": float(c_lng), "zone_id": zone_id})

        ring = _ring(z)
        if len(ring) < 3:
            continue

        rng = random.Random(f"{zone_id}:{len(ring)}:{round(spacing_km, 3)}")
        area_km2 = _polygon_area_km2(ring)
        target = max(4, min(35, int(round(area_km2 / max(spacing_km * spacing_km, 0.02)))))
        min_lat, max_lat, min_lng, max_lng = _bbox_lat_lng(ring)

        # Rejection sample random points inside polygon (strictly interior-ish).
        attempts = 0
        accepted = 0
        max_attempts = target * 80
        while accepted < target and attempts < max_attempts:
            attempts += 1
            lat = rng.uniform(min_lat, max_lat)
            lng = rng.uniform(min_lng, max_lng)
            if not _point_in_polygon(lat, lng, ring):
                continue
            # Keep samples away from centroid slightly for nicer spread.
            radial = math.sqrt((lat - c_lat) ** 2 + (lng - c_lng) ** 2)
            if radial < 0.0003 and rng.random() < 0.7:
                continue
            result.append({"lat": float(lat), "lng": float(lng), "zone_id": zone_id})
            accepted += 1

    return _dedupe(result)
