"""Graph construction + Dijkstra routing."""
from __future__ import annotations

import networkx as nx
from shapely.geometry import Polygon

from relayroute.models import DropoffPoint, Zone


def _point_in_polygon(lat: float, lng: float, polygon: dict) -> bool:
    coords = (polygon or {}).get("coordinates", [[]])
    if not coords or not coords[0]:
        return False
    ring = coords[0]
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _zone_centroid(boundaries: dict) -> tuple[float, float]:
    coords = (boundaries or {}).get("coordinates", [[]])
    if not coords or not coords[0]:
        return (0.0, 0.0)
    ring = coords[0]
    lat = sum(p[1] for p in ring) / len(ring)
    lng = sum(p[0] for p in ring) / len(ring)
    return (lat, lng)


def build_graph(
    zones: list[Zone],
    dropoff_points: list[DropoffPoint],
    travel_times: dict,
) -> nx.DiGraph:
    """
    Build a graph where zone nodes are connected with weighted edges.
    Drop-off nodes are included as attributes and used for relay conversion.
    """
    graph = nx.DiGraph()
    active_dropoffs = [d for d in dropoff_points if d.status not in ("full", "disabled")]

    for z in zones:
        graph.add_node(
            z.id,
            node_type="zone",
            centroid=_zone_centroid(z.boundaries),
        )

    zone_by_id = {z.id: z for z in zones}

    def _zone_polygon(z: Zone) -> Polygon | None:
        coords = (z.boundaries or {}).get("coordinates", [[]])
        if not coords or not coords[0] or len(coords[0]) < 4:
            return None
        try:
            poly = Polygon(coords[0])
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                return None
            return poly
        except Exception:
            return None

    polygons = {z.id: _zone_polygon(z) for z in zones}

    # Build adjacency from polygon contact (touch/overlap/intersection).
    adjacency: dict[str, set[str]] = {z.id: set() for z in zones}
    for i, a in enumerate(zones):
        pa = polygons.get(a.id)
        for j in range(i + 1, len(zones)):
            b = zones[j]
            pb = polygons.get(b.id)
            if pa is not None and pb is not None and (pa.touches(pb) or pa.intersects(pb)):
                adjacency[a.id].add(b.id)
                adjacency[b.id].add(a.id)

    # Connectivity fallback: if a zone has no neighbors, connect to nearest 2 centroids.
    centroids = {z.id: _zone_centroid(z.boundaries) for z in zones}
    for z in zones:
        if adjacency[z.id]:
            continue
        zc = centroids[z.id]
        nearest = sorted(
            (other.id for other in zones if other.id != z.id),
            key=lambda oid: (zc[0] - centroids[oid][0]) ** 2 + (zc[1] - centroids[oid][1]) ** 2,
        )[:2]
        for oid in nearest:
            adjacency[z.id].add(oid)
            adjacency[oid].add(z.id)

    # Zone-zone edges with travel-time base weight across adjacency only.
    for a_id, nbrs in adjacency.items():
        for b_id in nbrs:
            weight = float(travel_times.get((a_id, b_id), 999.0))
            graph.add_edge(a_id, b_id, weight=weight)

    # Keep dropoff data available for path-to-relay conversion.
    for d in active_dropoffs:
        graph.add_node(
            d.id,
            node_type="dropoff",
            zone_id=d.zone_id,
            coords={"lat": d.lat, "lng": d.lng},
        )
    return graph


def dijkstra(
    graph: nx.DiGraph,
    origin_zone_id: str,
    destination_zone_id: str,
) -> tuple[list[str], float]:
    """Run Dijkstra path and return (node_path, total_weight)."""
    try:
        path = nx.dijkstra_path(graph, origin_zone_id, destination_zone_id, weight="weight")
        total = nx.path_weight(graph, path, weight="weight")
        return path, float(total)
    except nx.NetworkXNoPath as exc:
        raise RuntimeError("No routing path exists between origin and destination zones") from exc


def path_to_relay_chain(
    path: list[str],
    zones: dict,
    dropoffs: dict,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
) -> list[dict]:
    """
    Convert zone path into relay chain [{zone_id, dropoff_point_id, coords}].
    For each zone transition, select a dropoff in the *next* zone that is
    closest to the current handoff location (origin for first hop, then the
    previously chosen dropoff).
    """
    dropoffs_by_zone: dict[str, list[dict]] = {}
    for d in dropoffs.values():
        dropoffs_by_zone.setdefault(d.zone_id, []).append(d)

    current_lat = float(origin_lat) if origin_lat is not None else None
    current_lng = float(origin_lng) if origin_lng is not None else None

    if len(path) < 2:
        return []

    relay_chain: list[dict] = []
    for i in range(len(path) - 1):
        next_zone_id = path[i + 1]
        candidates = dropoffs_by_zone.get(next_zone_id, [])
        if not candidates:
            raise RuntimeError(f"No active dropoff available in next zone {next_zone_id}")
        zone_obj = zones.get(next_zone_id)
        if zone_obj is None:
            raise RuntimeError(f"Zone {next_zone_id} not found for relay conversion")

        in_zone_candidates = [
            d for d in candidates if _point_in_polygon(float(d.lat), float(d.lng), zone_obj.boundaries)
        ]
        if not in_zone_candidates:
            raise RuntimeError(f"No in-zone dropoff available in next zone {next_zone_id}")

        if current_lat is None or current_lng is None:
            cz_lat, cz_lng = _zone_centroid(zone_obj.boundaries)
            current_lat, current_lng = cz_lat, cz_lng

        dp = min(
            in_zone_candidates,
            key=lambda cand: (float(cand.lat) - current_lat) ** 2 + (float(cand.lng) - current_lng) ** 2,
        )
        relay_chain.append(
            {
                "zone_id": next_zone_id,
                "dropoff_point_id": dp.id,
                "coords": {"lat": dp.lat, "lng": dp.lng},
            }
        )
        current_lat = float(dp.lat)
        current_lng = float(dp.lng)
    return relay_chain
