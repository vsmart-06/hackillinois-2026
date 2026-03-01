"""Export authenticated city zones as GeoJSON.

Usage:
  python scripts/export_zone_geojson.py --api-key "<CITY_API_KEY>"

Optional:
  python scripts/export_zone_geojson.py --api-key "<CITY_API_KEY>" --base-url http://127.0.0.1:8000 --output zones.geojson
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def fetch_json(client: httpx.Client, url: str, headers: dict[str, str]) -> dict | list:
    resp = client.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"{url} -> {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def build_feature_collection(base_url: str, api_key: str) -> dict:
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
                    "city_id": city_id,
                    "city_name": city_name,
                    "zone_id": zone_detail.get("zone_id", zone_id),
                    "zone_name": zone_detail.get("name"),
                    "restaurant_count": zone_detail.get("restaurant_count"),
                },
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export zones to GeoJSON")
    parser.add_argument("--api-key", required=True, help="City app API key from POST /app/setup")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="RelayRoute API base URL")
    parser.add_argument("--output", default="zones.geojson", help="Output GeoJSON file path")
    args = parser.parse_args()

    try:
        feature_collection = build_feature_collection(args.base_url.rstrip("/"), args.api_key)
        output_path = Path(args.output).expanduser().resolve()
        output_path.write_text(json.dumps(feature_collection, indent=2), encoding="utf-8")
        print(f"Wrote {len(feature_collection['features'])} zone features to: {output_path}")
        return 0
    except Exception as exc:
        print(f"Failed to export GeoJSON: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
