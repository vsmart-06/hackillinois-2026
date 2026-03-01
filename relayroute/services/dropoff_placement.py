"""
Drop-off point placement on zone borders.
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


def _segment_len_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b
    mean_lat = math.radians((lat1 + lat2) / 2.0)
    d_lat_km = (lat2 - lat1) * 111.0
    d_lng_km = (lng2 - lng1) * (111.320 * max(math.cos(mean_lat), 0.1))
    return math.sqrt(d_lat_km * d_lat_km + d_lng_km * d_lng_km)


def _offset_km_to_deg(lat: float, dy_km: float, dx_km: float) -> tuple[float, float]:
    d_lat = dy_km / 111.0
    d_lng = dx_km / (111.320 * max(math.cos(math.radians(lat)), 0.1))
    return d_lat, d_lng


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
    Place drop-off points along each zone boundary with spacing and light random jitter.
    Also place one at each zone centroid as fallback.
    Return list of {lat, lng, zone_id}.
    """
    result: list[dict] = []
    for z in zones:
        zone_id = z["id"]
        c_lat, c_lng = _centroid(z)
        result.append({"lat": float(c_lat), "lng": float(c_lng), "zone_id": zone_id})

        ring = _ring(z)
        if len(ring) < 2:
            continue

        rng = random.Random(f"{zone_id}:{len(ring)}:{round(spacing_km, 3)}")
        for i in range(len(ring) - 1):
            a = ring[i]
            b = ring[i + 1]
            seg_km = _segment_len_km(a, b)
            steps = max(1, int(seg_km / max(spacing_km, 0.05)))
            for k in range(steps):
                t = (k + 0.5) / steps
                lat = a[0] + t * (b[0] - a[0])
                lng = a[1] + t * (b[1] - a[1])

                # Move slightly inward toward centroid, then add tiny tangent jitter
                v_lat = c_lat - lat
                v_lng = c_lng - lng
                mag = math.sqrt(v_lat * v_lat + v_lng * v_lng) or 1e-9
                n_lat = v_lat / mag
                n_lng = v_lng / mag
                inward_km = 0.04 + 0.05 * rng.random()  # 40-90m inward
                dlat_in, dlng_in = _offset_km_to_deg(lat, n_lat * inward_km, n_lng * inward_km)

                # Tangent direction for visual variation (about +/- 30m)
                t_lat = -(b[1] - a[1])
                t_lng = b[0] - a[0]
                t_mag = math.sqrt(t_lat * t_lat + t_lng * t_lng) or 1e-9
                t_lat /= t_mag
                t_lng /= t_mag
                tangent_km = (rng.random() - 0.5) * 0.06
                dlat_t, dlng_t = _offset_km_to_deg(lat, t_lat * tangent_km, t_lng * tangent_km)

                result.append(
                    {
                        "lat": float(lat + dlat_in + dlat_t),
                        "lng": float(lng + dlng_in + dlng_t),
                        "zone_id": zone_id,
                    }
                )

    return _dedupe(result)
