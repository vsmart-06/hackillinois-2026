"""
DBSCAN zone partitioning and zone boundary computation.
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull


def cluster_restaurants(
    restaurants: list[dict],
    epsilon_km: float,
    min_samples: int,
) -> list[list[dict]]:
    """
    Run DBSCAN on restaurant coordinates. Convert epsilon_km to radians for haversine.
    Return list of clusters (each cluster is a list of restaurant dicts).
    Assign noise points (label == -1) to nearest cluster.
    """
    if not restaurants:
        return []
    coords = []
    for r in restaurants:
        lat, lng = r.get("lat"), r.get("lng")
        if lat is not None and lng is not None:
            coords.append([math.radians(lat), math.radians(lng)])
    if not coords:
        return []
    X = np.array(coords)
    epsilon_rad = epsilon_km / 6371.0
    clustering = DBSCAN(eps=epsilon_rad, min_samples=min_samples, metric="haversine", algorithm="ball_tree")
    labels = clustering.fit_predict(X)
    n_clusters = max(labels) + 1
    clusters: list[list[dict]] = [[] for _ in range(n_clusters)]
    noise_indices: list[int] = []
    for i, label in enumerate(labels):
        r = restaurants[i]
        if label == -1:
            noise_indices.append(i)
        else:
            clusters[label].append(r)
    for i in noise_indices:
        r = restaurants[i]
        lat, lng = r.get("lat"), r.get("lng")
        if lat is None or lng is None:
            continue
        min_dist = float("inf")
        best_c = -1
        for c_idx, cluster in enumerate(clusters):
            for o in cluster:
                olat, olng = o.get("lat"), o.get("lng")
                if olat is None or olng is None:
                    continue
                d = (math.radians(lat) - math.radians(olat)) ** 2 + (math.radians(lng) - math.radians(olng)) ** 2
                if d < min_dist:
                    min_dist = d
                    best_c = c_idx
        if best_c >= 0:
            clusters[best_c].append(r)
    return [c for c in clusters if c]


def compute_zone_boundaries(cluster: list[dict]) -> dict:
    """
    Given a cluster of restaurants, compute a convex hull as a GeoJSON polygon.
    Add a small buffer (0.01 degrees) around the hull.
    Return GeoJSON-compatible dict.
    """
    if len(cluster) < 3:
        points = [(r["lat"], r["lng"]) for r in cluster if r.get("lat") is not None and r.get("lng") is not None]
        if len(points) < 2:
            if points:
                lat, lng = points[0]
                buffer = 0.01
                return {
                    "type": "Polygon",
                    "coordinates": [[
                        [lng - buffer, lat - buffer],
                        [lng + buffer, lat - buffer],
                        [lng + buffer, lat + buffer],
                        [lng - buffer, lat + buffer],
                        [lng - buffer, lat - buffer],
                    ]],
                }
            return {"type": "Polygon", "coordinates": []}
        if len(points) == 2:
            (lat1, lng1), (lat2, lng2) = points
            buffer = 0.01
            return {
                "type": "Polygon",
                "coordinates": [[
                    [lng1 - buffer, lat1 - buffer],
                    [lng2 + buffer, lat1 - buffer],
                    [lng2 + buffer, lat2 + buffer],
                    [lng1 - buffer, lat2 + buffer],
                    [lng1 - buffer, lat1 - buffer],
                ]],
            }
    points = np.array([(r["lat"], r["lng"]) for r in cluster if r.get("lat") is not None and r.get("lng") is not None])
    if len(points) < 3:
        return compute_zone_boundaries([{"lat": p[0], "lng": p[1]} for p in points])
    buffer = 0.01
    try:
        hull = ConvexHull(points)
        vertices = points[hull.vertices]
        expanded = []
        centroid = points.mean(axis=0)
        for v in vertices:
            d = v - centroid
            n = np.linalg.norm(d)
            if n > 1e-10:
                d = d / n * (n + buffer)
            else:
                d = np.array([buffer, buffer])
            expanded.append(centroid + d)
        ring = np.vstack([expanded, expanded[0:1]])
        coords = [[float(p[1]), float(p[0])] for p in ring]
        return {"type": "Polygon", "coordinates": [coords]}
    except Exception:
        # Collinear/degenerate points: fallback to buffered bounding box.
        min_lat = float(points[:, 0].min()) - buffer
        max_lat = float(points[:, 0].max()) + buffer
        min_lng = float(points[:, 1].min()) - buffer
        max_lng = float(points[:, 1].max()) + buffer
        return {
            "type": "Polygon",
            "coordinates": [[
                [min_lng, min_lat],
                [max_lng, min_lat],
                [max_lng, max_lat],
                [min_lng, max_lat],
                [min_lng, min_lat],
            ]],
        }
