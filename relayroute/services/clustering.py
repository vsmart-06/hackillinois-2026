"""
DBSCAN zone partitioning and zone boundary computation.
Voronoi regions are clipped to the city bounding box using Shapely.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPoint, Point, Polygon, box
from sklearn.cluster import DBSCAN


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


def _cluster_points(cluster: list[dict]) -> np.ndarray:
    pts = [(float(r["lng"]), float(r["lat"])) for r in cluster if r.get("lat") is not None and r.get("lng") is not None]
    if not pts:
        return np.empty((0, 2), dtype=float)
    return np.array(pts, dtype=float)


def _bbox_from_clusters(clusters: list[list[dict]], pad: float = 0.01) -> tuple[float, float, float, float]:
    all_pts = np.vstack([p for p in (_cluster_points(c) for c in clusters) if len(p) > 0])
    min_x = float(all_pts[:, 0].min()) - pad
    max_x = float(all_pts[:, 0].max()) + pad
    min_y = float(all_pts[:, 1].min()) - pad
    max_y = float(all_pts[:, 1].max()) + pad
    return (min_x, max_x, min_y, max_y)


def _bbox_polygon(bbox: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    min_x, max_x, min_y, max_y = bbox
    return [
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    ]


def _bbox_shapely(bbox: tuple[float, float, float, float]) -> Polygon:
    """City bounding box as a Shapely polygon (minx, miny, maxx, maxy)."""
    min_x, max_x, min_y, max_y = bbox
    return box(min_x, min_y, max_x, max_y)


def _city_mask_from_clusters(clusters: list[list[dict]], bbox: tuple[float, float, float, float]) -> Polygon:
    """
    Build a non-rectangular city mask from all restaurant points.
    Falls back to bbox when geometry is degenerate.
    """
    points: list[tuple[float, float]] = []
    for c in clusters:
        pts = _cluster_points(c)
        for p in pts:
            points.append((float(p[0]), float(p[1])))
    if len(points) < 3:
        return _bbox_shapely(bbox)
    try:
        hull = MultiPoint([Point(x, y) for x, y in points]).convex_hull
        # Light outward buffer to avoid clipping near-edge restaurants.
        buffered = hull.buffer(0.005)
        if buffered.is_empty or buffered.geom_type not in {"Polygon", "MultiPolygon"}:
            return _bbox_shapely(bbox)
        mask = buffered.intersection(_bbox_shapely(bbox))
        if mask.is_empty:
            return _bbox_shapely(bbox)
        if mask.geom_type == "MultiPolygon":
            return max(mask.geoms, key=lambda g: g.area)
        return mask
    except Exception:
        return _bbox_shapely(bbox)


def _close_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    if points[0] != points[-1]:
        return [*points, points[0]]
    return points


def _clip_voronoi_to_bbox(
    poly_points: list[tuple[float, float]],
    bbox_polygon: Polygon,
) -> list[tuple[float, float]]:
    """
    Clip a Voronoi region to the city bounding box using Shapely intersection.
    Returns the exterior ring of the clipped polygon, or empty list if invalid/empty.
    """
    if not poly_points or len(poly_points) < 3:
        return []
    try:
        voronoi_poly = Polygon(poly_points)
        if not voronoi_poly.is_valid:
            voronoi_poly = voronoi_poly.buffer(0)
        if voronoi_poly.is_empty:
            return []
        intersected = voronoi_poly.intersection(bbox_polygon)
        if intersected.is_empty:
            return []
        if intersected.geom_type == "Polygon":
            coords = list(intersected.exterior.coords)
            return [(float(x), float(y)) for x, y in coords]
        if intersected.geom_type == "MultiPolygon":
            # Use the polygon with largest area (main region)
            best = max(intersected.geoms, key=lambda g: g.area)
            coords = list(best.exterior.coords)
            return [(float(x), float(y)) for x, y in coords]
        if intersected.geom_type == "GeometryCollection":
            polygons = [g for g in intersected.geoms if g.geom_type == "Polygon" and not g.is_empty]
            if not polygons:
                return []
            best = max(polygons, key=lambda g: g.area)
            coords = list(best.exterior.coords)
            return [(float(x), float(y)) for x, y in coords]
        return []
    except Exception:
        return []


def _tiny_cell_around_centroid(
    centroid: tuple[float, float],
    city_mask: Polygon,
) -> list[tuple[float, float]]:
    """
    Tiny fallback cell near centroid to avoid whole-bbox overlaps when one Voronoi
    region cannot be clipped.
    """
    try:
        cell = Point(float(centroid[0]), float(centroid[1])).buffer(0.003)
        clipped = cell.intersection(city_mask)
        if clipped.is_empty:
            return []
        if clipped.geom_type == "Polygon":
            return [(float(x), float(y)) for x, y in clipped.exterior.coords]
        if clipped.geom_type == "MultiPolygon":
            best = max(clipped.geoms, key=lambda g: g.area)
            return [(float(x), float(y)) for x, y in best.exterior.coords]
        return []
    except Exception:
        return []


def _voronoi_finite_polygons_2d(vor: Voronoi, radius: float | None = None):
    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")
    new_regions: list[list[int]] = []
    new_vertices = vor.vertices.tolist()
    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max() * 2

    all_ridges: dict[int, list[tuple[int, int, int]]] = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue

        ridges = all_ridges.get(p1, [])
        new_region = [v for v in vertices if v >= 0]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue
            tangent = vor.points[p2] - vor.points[p1]
            tangent /= np.linalg.norm(tangent)
            normal = np.array([-tangent[1], tangent[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, normal)) * normal
            far_point = vor.vertices[v2] + direction * radius
            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = [v for _, v in sorted(zip(angles, new_region))]
        new_regions.append(new_region)

    return new_regions, np.asarray(new_vertices)


def _fallback_split_polygons(centroids: np.ndarray, bbox: tuple[float, float, float, float]) -> list[list[tuple[float, float]]]:
    min_x, max_x, min_y, max_y = bbox
    n = len(centroids)
    if n == 1:
        return [_bbox_polygon(bbox)]
    if n == 2:
        c1, c2 = centroids[0], centroids[1]
        if abs(float(c1[0]) - float(c2[0])) >= abs(float(c1[1]) - float(c2[1])):
            mid_x = float((c1[0] + c2[0]) / 2.0)
            left = [(min_x, min_y), (mid_x, min_y), (mid_x, max_y), (min_x, max_y)]
            right = [(mid_x, min_y), (max_x, min_y), (max_x, max_y), (mid_x, max_y)]
            return [left, right] if c1[0] <= c2[0] else [right, left]
        mid_y = float((c1[1] + c2[1]) / 2.0)
        bottom = [(min_x, min_y), (max_x, min_y), (max_x, mid_y), (min_x, mid_y)]
        top = [(min_x, mid_y), (max_x, mid_y), (max_x, max_y), (min_x, max_y)]
        return [bottom, top] if c1[1] <= c2[1] else [top, bottom]

    order = np.argsort(centroids[:, 0])
    splits: list[float] = [float(min_x)]
    sorted_x = centroids[order, 0]
    for i in range(n - 1):
        splits.append(float((sorted_x[i] + sorted_x[i + 1]) / 2.0))
    splits.append(float(max_x))
    polys: list[list[tuple[float, float]]] = [None] * n  # type: ignore[list-item]
    for rank, idx in enumerate(order):
        polys[idx] = [
            (splits[rank], min_y),
            (splits[rank + 1], min_y),
            (splits[rank + 1], max_y),
            (splits[rank], max_y),
        ]
    return polys


def compute_zone_boundaries(clusters: list[list[dict]]) -> list[dict]:
    """
    Compute zone polygons using centroid-based Voronoi partitioning.

    Steps:
    1) Compute centroid for each DBSCAN cluster.
    2) Build Voronoi regions from centroids.
    3) Clip each region to the city's bounding box.
    4) Return GeoJSON polygons in the same order as clusters.
    """
    if not clusters:
        return []

    bbox = _bbox_from_clusters(clusters)
    centroids: list[np.ndarray] = []
    for cluster in clusters:
        pts = _cluster_points(cluster)
        if len(pts) == 0:
            min_x, max_x, min_y, max_y = bbox
            centroids.append(np.array([(min_x + max_x) / 2.0, (min_y + max_y) / 2.0]))
        else:
            centroids.append(pts.mean(axis=0))
    centroid_arr = np.array(centroids, dtype=float)

    city_mask = _city_mask_from_clusters(clusters, bbox)
    polygons: list[list[tuple[float, float]]]
    if len(centroid_arr) < 3:
        polygons = _fallback_split_polygons(centroid_arr, bbox)
    else:
        try:
            vor = Voronoi(centroid_arr)
            regions, vertices = _voronoi_finite_polygons_2d(vor)
            polygons = []
            for idx, region in enumerate(regions):
                poly = [(float(vertices[i][0]), float(vertices[i][1])) for i in region]
                clipped = _clip_voronoi_to_bbox(poly, city_mask)
                if not clipped:
                    clipped = _tiny_cell_around_centroid((float(centroid_arr[idx][0]), float(centroid_arr[idx][1])), city_mask)
                polygons.append(clipped if clipped else _bbox_polygon(bbox))
        except Exception:
            jitter = np.array([[i * 5e-6, -i * 5e-6] for i in range(len(centroid_arr))], dtype=float)
            try:
                vor = Voronoi(centroid_arr + jitter)
                regions, vertices = _voronoi_finite_polygons_2d(vor)
                polygons = []
                for idx, region in enumerate(regions):
                    poly = [(float(vertices[i][0]), float(vertices[i][1])) for i in region]
                    clipped = _clip_voronoi_to_bbox(poly, city_mask)
                    if not clipped:
                        clipped = _tiny_cell_around_centroid(
                            (float((centroid_arr + jitter)[idx][0]), float((centroid_arr + jitter)[idx][1])),
                            city_mask,
                        )
                    polygons.append(clipped if clipped else _bbox_polygon(bbox))
            except Exception:
                polygons = _fallback_split_polygons(centroid_arr, bbox)

    geojson: list[dict] = []
    bbox_ring = _close_ring(_bbox_polygon(bbox))
    bbox_coords = [[float(x), float(y)] for x, y in bbox_ring]
    for poly in polygons:
        ring = _close_ring(poly)
        coords = [[float(x), float(y)] for x, y in ring]
        if not coords:
            coords = bbox_coords
        geojson.append({"type": "Polygon", "coordinates": [coords]})
    return geojson
