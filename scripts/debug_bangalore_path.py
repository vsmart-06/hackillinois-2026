"""Debug a specific Bangalore routing scenario."""

from __future__ import annotations

import httpx


def in_poly(lat: float, lng: float, poly: dict) -> bool:
    coords = (poly or {}).get("coordinates", [[]])
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


def main() -> int:
    base = "http://127.0.0.1:8000"
    target_name = "The Rogue Elephant Basavanagudi"
    destination = "Vaishnavi Orchids"
    payload = {
        "city_name": "Bangalore",
        "epsilon_km": 0.3,
        "min_restaurants_per_zone": 3,
        "dropoff_spacing_km": 0.25,
        "dropoff_capacity": 15,
    }

    with httpx.Client(timeout=240.0) as client:
        setup = client.post(f"{base}/app/setup", json=payload)
        print("setup_status", setup.status_code)
        if setup.status_code != 201:
            print(setup.text[:600])
            return 1
        setup_json = setup.json()
        headers = {"X-API-Key": setup_json["api_key"]}
        print(
            "counts",
            len(setup_json.get("zones", [])),
            len(setup_json.get("restaurants", [])),
            len(setup_json.get("dropoff_points", [])),
        )
        print("cities_status", client.get(f"{base}/app/cities", headers=headers).status_code)

        restaurants = setup_json.get("restaurants", [])
        exact = [r for r in restaurants if (r.get("name") or "").strip().lower() == target_name.lower()]
        fuzzy = [r for r in restaurants if "rogue elephant" in (r.get("name") or "").lower()]
        if exact:
            restaurant = exact[0]
            print("exact_match", True)
        elif fuzzy:
            restaurant = fuzzy[0]
            print("exact_match", False)
            print("fuzzy_candidates", [f.get("name") for f in fuzzy[:5]])
        else:
            print("restaurant_not_found")
            return 2

        print(
            "restaurant",
            {
                "id": restaurant.get("id"),
                "name": restaurant.get("name"),
                "zone_id": restaurant.get("zone_id"),
                "lat": restaurant.get("lat"),
                "lng": restaurant.get("lng"),
            },
        )

        order = client.post(
            f"{base}/app/orders",
            headers=headers,
            json={
                "city_id": setup_json["city_id"],
                "restaurant_id": restaurant["id"],
                "delivery_address": destination,
            },
        )
        print("order_status", order.status_code)
        if order.status_code != 200:
            print(order.text[:600])
            return 3
        order_json = order.json()
        print(
            "order_create",
            {
                "order_id": order_json.get("order_id"),
                "estimated_handoffs": order_json.get("estimated_handoffs"),
                "relay_chain_len": len(order_json.get("relay_chain") or []),
                "relay_chain": order_json.get("relay_chain"),
            },
        )

        detail_resp = client.get(f"{base}/app/orders/{order_json['order_id']}", headers=headers)
        print("order_detail_status", detail_resp.status_code)
        detail = detail_resp.json()
        print(
            "order_detail",
            {
                "status": detail.get("status"),
                "current_zone_id": detail.get("current_zone_id"),
                "delivery_lat": detail.get("delivery_lat"),
                "delivery_lng": detail.get("delivery_lng"),
                "relay_chain_len": len(detail.get("relay_chain") or []),
            },
        )

        destination_zone = None
        for z in setup_json.get("zones", []):
            if in_poly(float(detail["delivery_lat"]), float(detail["delivery_lng"]), z.get("boundaries")):
                destination_zone = z.get("id")
                break
        print(
            "zone_check",
            {
                "restaurant_zone": restaurant.get("zone_id"),
                "destination_zone": destination_zone,
                "same_zone": restaurant.get("zone_id") == destination_zone,
            },
        )

        routing_resp = client.get(
            f"{base}/app/routing/path",
            headers=headers,
            params={
                "origin_lat": restaurant["lat"],
                "origin_lng": restaurant["lng"],
                "destination_lat": detail["delivery_lat"],
                "destination_lng": detail["delivery_lng"],
            },
        )
        print("routing_status", routing_resp.status_code)
        if routing_resp.status_code == 200:
            print("routing", routing_resp.json())
        else:
            print(routing_resp.text[:600])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
