"""RelayRoute API smoke test runner.

Usage:
  1) Start the API in another terminal:
       uvicorn relayroute.main:app --host 127.0.0.1 --port 8000 --reload
  2) Run:
       python scripts/smoke_test.py

Optional:
  python scripts/smoke_test.py --base-url http://127.0.0.1:8001
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import httpx


@dataclass
class CheckResult:
    name: str
    ok: bool
    status_code: int | None = None
    detail: str | None = None


def run_smoke(base_url: str) -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    failures = 0

    with httpx.Client(timeout=120.0) as client:
        # 1) Basic health/docs checks
        for path in ("/docs", "/openapi.json", "/redoc"):
            try:
                resp = client.get(f"{base_url}{path}")
                ok = resp.status_code == 200
                results.append(
                    CheckResult(
                        name=f"GET {path}",
                        ok=ok,
                        status_code=resp.status_code,
                        detail=None if ok else resp.text[:300],
                    )
                )
                if not ok:
                    failures += 1
            except Exception as exc:
                results.append(CheckResult(name=f"GET {path}", ok=False, detail=str(exc)))
                failures += 1

        # 2) Setup call (depends on external APIs + DB)
        setup_payload = {
            "city_name": "Champaign Illinois",
            "epsilon_km": 0.8,
            "min_restaurants_per_zone": 8,
            "dropoff_spacing_km": 0.4,
            "dropoff_capacity": 15,
        }
        city_id: str | None = None
        api_key: str | None = None
        first_restaurant_id: str | None = None
        first_zone_id: str | None = None
        first_dropoff_id: str | None = None
        first_restaurant_coords: tuple[float, float] | None = None

        try:
            resp = client.post(f"{base_url}/app/setup", json=setup_payload)
            ok = resp.status_code == 201
            detail = None
            if not ok:
                try:
                    detail = json.dumps(resp.json())
                except Exception:
                    detail = resp.text[:600]
            else:
                body = resp.json()
                city_id = body.get("city_id")
                api_key = body.get("api_key")
                restaurants = body.get("restaurants", [])
                zones = body.get("zones", [])
                dropoffs = body.get("dropoff_points", [])
                if restaurants:
                    first_restaurant_id = restaurants[0].get("id")
                    first_restaurant_coords = (
                        float(restaurants[0].get("lat")),
                        float(restaurants[0].get("lng")),
                    )
                if zones:
                    first_zone_id = zones[0].get("id")
                if dropoffs:
                    first_dropoff_id = dropoffs[0].get("id")

            results.append(
                CheckResult(
                    name="POST /app/setup",
                    ok=ok,
                    status_code=resp.status_code,
                    detail=detail,
                )
            )
            if not ok:
                failures += 1
        except Exception as exc:
            results.append(CheckResult(name="POST /app/setup", ok=False, detail=str(exc)))
            failures += 1

        # If setup succeeded, run authenticated flow checks.
        if city_id and api_key:
            headers = {"X-API-Key": api_key}

            def check(method: str, path: str, expected: tuple[int, ...], **kwargs) -> None:
                nonlocal failures
                try:
                    resp2 = client.request(method, f"{base_url}{path}", **kwargs)
                    ok2 = resp2.status_code in expected
                    results.append(
                        CheckResult(
                            name=f"{method} {path}",
                            ok=ok2,
                            status_code=resp2.status_code,
                            detail=None if ok2 else resp2.text[:400],
                        )
                    )
                    if not ok2:
                        failures += 1
                except Exception as exc:
                    results.append(CheckResult(name=f"{method} {path}", ok=False, detail=str(exc)))
                    failures += 1

            check("GET", "/app/setup", (200,), headers=headers)
            check("GET", "/app/zones", (200,), headers=headers)
            check("GET", "/app/orders", (200,), headers=headers)

            order_id: str | None = None
            if first_restaurant_id:
                order_payload = {
                    "city_id": city_id,
                    "restaurant_id": first_restaurant_id,
                    "delivery_address": "201 N Goodwin Ave, Urbana, IL 61801",
                }
                try:
                    r_order = client.post(f"{base_url}/app/orders", headers=headers, json=order_payload)
                    ok_order = r_order.status_code == 200
                    detail = None if ok_order else r_order.text[:400]
                    if ok_order:
                        order_id = r_order.json().get("order_id")
                    results.append(
                        CheckResult(
                            name="POST /app/orders",
                            ok=ok_order,
                            status_code=r_order.status_code,
                            detail=detail,
                        )
                    )
                    if not ok_order:
                        failures += 1
                except Exception as exc:
                    results.append(CheckResult(name="POST /app/orders", ok=False, detail=str(exc)))
                    failures += 1

            if order_id:
                check("GET", f"/app/orders/{order_id}/status", (200,), headers=headers)
                check("GET", f"/app/orders/{order_id}", (200,), headers=headers)

            if first_zone_id:
                check("GET", f"/app/zones/{first_zone_id}", (200,), headers=headers)
                check("GET", f"/app/zones/{first_zone_id}/load", (200,), headers=headers)

            if first_dropoff_id:
                check("GET", f"/app/dropoffs/{first_dropoff_id}", (200,), headers=headers)
                check(
                    "PATCH",
                    f"/app/dropoffs/{first_dropoff_id}/status",
                    (200,),
                    headers=headers,
                    json={"status": "full"},
                )
                # restore to active so test run is less destructive
                check(
                    "PATCH",
                    f"/app/dropoffs/{first_dropoff_id}/status",
                    (200,),
                    headers=headers,
                    json={"status": "active"},
                )

            if first_restaurant_coords:
                lat, lng = first_restaurant_coords
                params = {
                    "origin_lat": lat,
                    "origin_lng": lng,
                    "destination_lat": lat + 0.02,
                    "destination_lng": lng + 0.02,
                }
                check("GET", "/app/routing/path", (200,), headers=headers, params=params)

            # Partner registration/auth smoke checks
            if first_zone_id:
                reg_payload = {
                    "name": "Smoke Partner",
                    "phone": "+1-000-000-0000",
                    "zone_id": first_zone_id,
                    "city_id": city_id,
                }
                r_reg = client.post(
                    f"{base_url}/partner/register",
                    json=reg_payload,
                )
                ok_reg = r_reg.status_code == 200
                results.append(
                    CheckResult(
                        name="POST /partner/register",
                        ok=ok_reg,
                        status_code=r_reg.status_code,
                        detail=None if ok_reg else r_reg.text[:400],
                    )
                )
                if not ok_reg:
                    failures += 1
                else:
                    partner_id = r_reg.json().get("partner_id")
                    partner_api_key = r_reg.json().get("api_key")
                    p_headers = {"X-API-Key": partner_api_key}
                    check("GET", "/partner", (200,), headers=p_headers)
                    check(
                        "PATCH",
                        "/partner/status",
                        (200,),
                        headers=p_headers,
                        json={"status": "available"},
                    )
                    check("GET", "/partner/next-task", (200,), headers=p_headers)

    return results, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="RelayRoute smoke test runner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    results, failures = run_smoke(args.base_url.rstrip("/"))

    print("\nRelayRoute Smoke Test Results")
    print("-" * 36)
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        code = f" ({item.status_code})" if item.status_code is not None else ""
        print(f"[{status}] {item.name}{code}")
        if item.detail and not item.ok:
            print(f"       detail: {item.detail}")

    print("-" * 36)
    print(f"Total checks: {len(results)}")
    print(f"Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
