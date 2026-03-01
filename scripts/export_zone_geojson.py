"""Export authenticated city map layers as GeoJSON.

Usage:
  python scripts/export_zone_geojson.py --api-key "<CITY_API_KEY>"

Optional:
  python scripts/export_zone_geojson.py --api-key "<CITY_API_KEY>" --base-url http://127.0.0.1:8000 --output zones.geojson --include-paths
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import httpx


def fetch_json(client: httpx.Client, url: str, headers: dict[str, str]) -> dict | list:
    resp = client.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"{url} -> {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _build_dropoff_features(dropoffs: Iterable[dict], city_id: str | None, city_name: str | None) -> list[dict]:
    features: list[dict] = []
    for d in dropoffs:
        lat = d.get("lat")
        lng = d.get("lng")
        if lat is None or lng is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)],
                },
                "properties": {
                    "feature_type": "dropoff",
                    "city_id": city_id,
                    "city_name": city_name,
                    "dropoff_id": d.get("id"),
                    "zone_id": d.get("zone_id"),
                    "status": d.get("status"),
                    "capacity": d.get("capacity"),
                    "current_load": d.get("current_load"),
                    "address": d.get("address"),
                },
            }
        )
    return features


def _build_order_path_feature(order: dict, city_id: str | None, city_name: str | None) -> dict | None:
    relay_chain = order.get("relay_chain") or []
    coords: list[list[float]] = []
    for step in relay_chain:
        if not isinstance(step, dict):
            continue
        step_coords = step.get("coords") or {}
        lat = step_coords.get("lat")
        lng = step_coords.get("lng")
        if lat is None or lng is None:
            continue
        coords.append([float(lng), float(lat)])

    if len(coords) < 2:
        return None

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "feature_type": "order_path",
            "city_id": city_id,
            "city_name": city_name,
            "order_id": order.get("order_id"),
            "status": order.get("status"),
            "estimated_handoffs": order.get("estimated_handoffs"),
            "remaining_handoffs": order.get("remaining_handoffs"),
        },
    }


def build_feature_collection(base_url: str, api_key: str, include_paths: bool) -> dict:
    headers = {"X-API-Key": api_key}
    with httpx.Client(timeout=60.0) as client:
        city_payload = fetch_json(client, f"{base_url}/app/cities", headers)
        city_entry = (city_payload.get("cities") or [{}])[0] if isinstance(city_payload, dict) else {}
        city_id = city_entry.get("city_id")
        city_name = city_entry.get("city_name")

        zones = fetch_json(client, f"{base_url}/app/zones", headers)
        if not isinstance(zones, list):
            raise RuntimeError("Unexpected /app/zones response shape; expected list")

        features: list[dict] = []
        for z in zones:
            zone_id = z.get("id")
            if not zone_id:
                continue
            zone_detail = fetch_json(client, f"{base_url}/app/zones/{zone_id}", headers)
            geometry = zone_detail.get("boundaries")
            if not geometry:
                continue

            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "feature_type": "zone",
                    "city_id": city_id,
                    "city_name": city_name,
                    "zone_id": zone_detail.get("zone_id", zone_id),
                    "zone_name": zone_detail.get("name"),
                    "restaurant_count": zone_detail.get("restaurant_count"),
                },
            }
            features.append(feature)

        dropoffs = fetch_json(client, f"{base_url}/app/dropoffs", headers)
        if isinstance(dropoffs, list):
            features.extend(_build_dropoff_features(dropoffs, city_id, city_name))

        if include_paths:
            orders = fetch_json(client, f"{base_url}/app/orders", headers)
            if isinstance(orders, list):
                for order in orders:
                    order_id = order.get("order_id")
                    if not order_id:
                        continue
                    order_detail = fetch_json(client, f"{base_url}/app/orders/{order_id}", headers)
                    if not isinstance(order_detail, dict):
                        continue
                    feature = _build_order_path_feature(order_detail, city_id, city_name)
                    if feature is not None:
                        features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export city map layers to GeoJSON")
    parser.add_argument("--api-key", required=True, help="City app API key from POST /app/setup")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="RelayRoute API base URL")
    parser.add_argument("--output", default="zones.geojson", help="Output GeoJSON file path")
    parser.add_argument(
        "--include-paths",
        action="store_true",
        help="Include active/generated order relay paths as LineString features",
    )
    args = parser.parse_args()

    try:
        feature_collection = build_feature_collection(
            args.base_url.rstrip("/"),
            args.api_key,
            include_paths=args.include_paths,
        )
        output_path = Path(args.output).expanduser().resolve()
        output_path.write_text(json.dumps(feature_collection, indent=2), encoding="utf-8")
        print(f"Wrote {len(feature_collection['features'])} features to: {output_path}")
        return 0
    except Exception as exc:
        print(f"Failed to export GeoJSON: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
