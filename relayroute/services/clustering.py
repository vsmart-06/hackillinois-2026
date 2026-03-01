"""
Demo-first zoning utilities.

This intentionally favors visually pleasing zones over density-driven clustering.
"""
from __future__ import annotations

import math


def _valid_restaurants(restaurants: list[dict]) -> list[dict]:
    return [r for r in restaurants if r.get("lat") is not None and r.get("lng") is not None]


def _city_center(restaurants: list[dict]) -> tuple[float, float]:
    lat = sum(float(r["lat"]) for r in restaurants) / len(restaurants)
    lng = sum(float(r["lng"]) for r in restaurants) / len(restaurants)
    return (lat, lng)


def _zone_count(restaurants: list[dict], min_samples: int) -> int:
    n = len(restaurants)
    if n <= 20:
        return 4
    if n <= 40:
        return 5
    if n <= 70:
        return 6
    return max(6, min(10, int(round(n / max(min_samples * 2, 12)))))


def cluster_restaurants(
    restaurants: list[dict],
    epsilon_km: float,
    min_samples: int,
) -> list[list[dict]]:
    """
    Assign restaurants to radial sectors around city center.

    epsilon_km is intentionally unused in this demo mode.
    """
    _ = epsilon_km
    valid = _valid_restaurants(restaurants)
    if not valid:
        return []

    center_lat, center_lng = _city_center(valid)
    zones_n = _zone_count(valid, min_samples)
    sector = (2.0 * math.pi) / zones_n
    buckets: list[list[dict]] = [[] for _ in range(zones_n)]

    for r in valid:
        dy = float(r["lat"]) - center_lat
        dx = float(r["lng"]) - center_lng
        angle = math.atan2(dy, dx)
        if angle < 0:
            angle += 2.0 * math.pi
        idx = min(zones_n - 1, int(angle / sector))
        buckets[idx].append(r)

    # Keep stable zone order but remove empty sectors.
    return [b for b in buckets if b]


def _city_radius_deg(clusters: list[list[dict]], center_lat: float, center_lng: float) -> float:
    max_r = 0.0
    for cluster in clusters:
        for r in cluster:
            dy = float(r["lat"]) - center_lat
            dx = float(r["lng"]) - center_lng
            max_r = max(max_r, math.sqrt(dx * dx + dy * dy))
    return max(max_r * 1.15, 0.02)


def compute_zone_boundaries(clusters: list[list[dict]]) -> list[dict]:
    """
    Build circular-ish wedge zones around the city center.

    Non-overlapping by construction and designed for visual clarity in demos.
    """
    if not clusters:
        return []

    all_restaurants = [r for c in clusters for r in c]
    center_lat, center_lng = _city_center(all_restaurants)
    zones_n = len(clusters)
    sector = (2.0 * math.pi) / zones_n
    base_radius = _city_radius_deg(clusters, center_lat, center_lng)

    boundaries: list[dict] = []
    arc_steps = 24
    for i in range(zones_n):
        start = i * sector
        end = (i + 1) * sector
        ring: list[list[float]] = [[center_lng, center_lat]]
        for j in range(arc_steps + 1):
            t = j / arc_steps
            ang = start + (end - start) * t
            # Soft ripple so zones are less perfectly geometric.
            ripple = 0.92 + 0.08 * math.sin((i + 1) * 1.7 + ang * 3.2)
            radius = base_radius * ripple
            lat = center_lat + radius * math.sin(ang)
            lng = center_lng + radius * math.cos(ang)
            ring.append([lng, lat])
        ring.append([center_lng, center_lat])
        boundaries.append({"type": "Polygon", "coordinates": [ring]})

    return boundaries
