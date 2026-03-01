"""Graph construction + Dijkstra routing."""
from __future__ import annotations

import networkx as nx

from relayroute.models import DropoffPoint, Zone


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

    # Zone-zone edges with travel-time base weight.
    for a in zones:
        for b in zones:
            if a.id == b.id:
                continue
            weight = float(travel_times.get((a.id, b.id), 999.0))
            graph.add_edge(a.id, b.id, weight=weight)

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
) -> list[dict]:
    """
    Convert zone path into relay chain [{zone_id, dropoff_point_id, coords}].
    Uses first available dropoff in each traversed zone.
    """
    dropoffs_by_zone: dict[str, list[dict]] = {}
    for d in dropoffs.values():
        dropoffs_by_zone.setdefault(d.zone_id, []).append(d)

    relay_chain: list[dict] = []
    for zone_id in path:
        candidates = dropoffs_by_zone.get(zone_id, [])
        if not candidates:
            continue
        dp = candidates[0]
        relay_chain.append(
            {
                "zone_id": zone_id,
                "dropoff_point_id": dp.id,
                "coords": {"lat": dp.lat, "lng": dp.lng},
            }
        )
    return relay_chain
