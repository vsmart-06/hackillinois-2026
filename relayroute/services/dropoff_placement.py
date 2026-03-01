"""
Drop-off point placement on zone borders.
"""
from __future__ import annotations

import math


def _centroid(zone: dict) -> tuple[float, float]:
    boundaries = zone.get("boundaries") or {}
    coords = boundaries.get("coordinates", [[]])
    if not coords or not coords[0]:
        return (zone.get("lat", 0.0), zone.get("lng", 0.0))
    ring = coords[0]
    lats = [p[1] for p in ring]
    lngs = [p[0] for p in ring]
    return (sum(lats) / len(lats), sum(lngs) / len(lngs))


def place_dropoff_points(
    zones: list[dict],
    spacing_km: float,
) -> list[dict]:
    """
    For each pair of adjacent zones, place drop-off points along the border at spacing_km.
    Also place one at each zone centroid as fallback.
    Return list of {lat, lng, zone_id}.
    """
    result: list[dict] = []
    n = len(zones)
    for i, z in enumerate(zones):
        c = _centroid(z)
        result.append({"lat": c[0], "lng": c[1], "zone_id": z["id"]})
    for i in range(n):
        for j in range(i + 1, n):
            zi, zj = zones[i], zones[j]
            ci = _centroid(zi)
            cj = _centroid(zj)
            mid_lat = (ci[0] + cj[0]) / 2
            mid_lng = (ci[1] + cj[1]) / 2
            result.append({"lat": mid_lat, "lng": mid_lng, "zone_id": zi["id"]})
            result.append({"lat": mid_lat, "lng": mid_lng, "zone_id": zj["id"]})
            dist_deg = math.sqrt((ci[0] - cj[0]) ** 2 + (ci[1] - cj[1]) ** 2)
            if dist_deg < 1e-6:
                continue
            km_per_deg = 111.0
            dist_km = dist_deg * km_per_deg
            steps = max(1, int(dist_km / spacing_km))
            for k in range(1, steps):
                t = k / steps
                lat = ci[0] + t * (cj[0] - ci[0])
                lng = ci[1] + t * (cj[1] - ci[1])
                result.append({"lat": lat, "lng": lng, "zone_id": zi["id"]})
                result.append({"lat": lat, "lng": lng, "zone_id": zj["id"]})
    return result
