"""Validate live API responses against documented response schemas.

Usage:
  python scripts/contract_check.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from relayroute.schemas.city import CityListResponse, CitySetupResponse, CityTopologyResponse
from relayroute.schemas.dropoff import DropoffDetailResponse, DropoffStatusResponse, DropoffSummary
from relayroute.schemas.order import (
    OrderDetailResponse,
    OrderListItem,
    OrderResponse,
    OrderStatusResponse,
    RelayHistoryResponse,
)
from relayroute.schemas.partner import (
    CompleteTaskResponse,
    NextTaskResponse,
    PartnerProfileResponse,
    PartnerRegisterResponse,
    PartnerStatusResponse,
    PartnerTaskHistoryResponse,
)
from relayroute.schemas.routing import RoutingResponse
from relayroute.schemas.zone import (
    ZoneDetailResponse,
    ZoneDropoffsResponse,
    ZoneLoadResponse,
    ZoneOrdersResponse,
    ZonePartnersResponse,
    ZoneSummary,
)


@dataclass
class ContractResult:
    endpoint: str
    ok: bool
    detail: str | None = None


def _validate(endpoint: str, payload: Any, adapter: TypeAdapter[Any]) -> ContractResult:
    try:
        adapter.validate_python(payload)
        return ContractResult(endpoint=endpoint, ok=True)
    except ValidationError as exc:
        return ContractResult(endpoint=endpoint, ok=False, detail=str(exc))


def run(base_url: str) -> tuple[list[ContractResult], int]:
    results: list[ContractResult] = []
    failures = 0

    zones_adapter = TypeAdapter(list[ZoneSummary])
    orders_adapter = TypeAdapter(list[OrderListItem])
    dropoffs_adapter = TypeAdapter(list[DropoffSummary])

    with httpx.Client(timeout=120.0) as client:
        setup_payload = {
            "city_name": "Champaign Illinois",
            "epsilon_km": 0.8,
            "min_restaurants_per_zone": 8,
            "dropoff_spacing_km": 0.4,
            "dropoff_capacity": 15,
        }
        setup_resp = client.post(f"{base_url}/app/setup", json=setup_payload)
        if setup_resp.status_code != 201:
            return [ContractResult("POST /app/setup", False, setup_resp.text[:500])], 1

        setup_json = setup_resp.json()
        r = _validate("POST /app/setup", setup_json, TypeAdapter(CitySetupResponse))
        results.append(r)
        failures += 0 if r.ok else 1

        city_id = setup_json["city_id"]
        city_api_key = setup_json["api_key"]
        first_zone_id = setup_json["zones"][0]["id"] if setup_json.get("zones") else None
        first_restaurant_id = setup_json["restaurants"][0]["id"] if setup_json.get("restaurants") else None
        first_dropoff_id = setup_json["dropoff_points"][0]["id"] if setup_json.get("dropoff_points") else None
        first_restaurant = setup_json["restaurants"][0] if setup_json.get("restaurants") else None
        app_headers = {"X-API-Key": city_api_key}

        def get_json(path: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
            resp = client.get(f"{base_url}{path}", headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"{path} returned {resp.status_code}: {resp.text[:300]}")
            return resp.json()

        def patch_json(path: str, body: dict[str, Any], *, headers: dict[str, str]) -> Any:
            resp = client.patch(f"{base_url}{path}", headers=headers, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"{path} returned {resp.status_code}: {resp.text[:300]}")
            return resp.json()

        checks: list[tuple[str, Any, TypeAdapter[Any]]] = []

        checks.append(("/app/setup", get_json("/app/setup", headers=app_headers), TypeAdapter(CityTopologyResponse)))
        checks.append(("/app/cities", get_json("/app/cities", headers=app_headers), TypeAdapter(CityListResponse)))
        checks.append(("/app/zones", get_json("/app/zones", headers=app_headers), zones_adapter))

        if first_zone_id:
            checks.append(
                (
                    f"/app/zones/{first_zone_id}",
                    get_json(f"/app/zones/{first_zone_id}", headers=app_headers),
                    TypeAdapter(ZoneDetailResponse),
                )
            )
            checks.append(
                (
                    f"/app/zones/{first_zone_id}/partners",
                    get_json(f"/app/zones/{first_zone_id}/partners", headers=app_headers),
                    TypeAdapter(ZonePartnersResponse),
                )
            )
            checks.append(
                (
                    f"/app/zones/{first_zone_id}/dropoffs",
                    get_json(f"/app/zones/{first_zone_id}/dropoffs", headers=app_headers),
                    TypeAdapter(ZoneDropoffsResponse),
                )
            )
            checks.append(
                (
                    f"/app/zones/{first_zone_id}/orders",
                    get_json(f"/app/zones/{first_zone_id}/orders", headers=app_headers),
                    TypeAdapter(ZoneOrdersResponse),
                )
            )
            checks.append(
                (
                    f"/app/zones/{first_zone_id}/load",
                    get_json(f"/app/zones/{first_zone_id}/load", headers=app_headers),
                    TypeAdapter(ZoneLoadResponse),
                )
            )

        checks.append(("/app/dropoffs", get_json("/app/dropoffs", headers=app_headers), dropoffs_adapter))

        order_id: str | None = None
        if first_restaurant_id:
            create_order_payload = {
                "city_id": city_id,
                "restaurant_id": first_restaurant_id,
                "delivery_address": "201 N Goodwin Ave, Urbana, IL 61801",
            }
            order_resp = client.post(f"{base_url}/app/orders", headers=app_headers, json=create_order_payload)
            if order_resp.status_code != 200:
                raise RuntimeError(f"/app/orders returned {order_resp.status_code}: {order_resp.text[:300]}")
            order_json = order_resp.json()
            checks.append(("/app/orders [POST]", order_json, TypeAdapter(OrderResponse)))
            order_id = order_json["order_id"]

        checks.append(("/app/orders", get_json("/app/orders", headers=app_headers), orders_adapter))

        if order_id:
            checks.append(
                (
                    f"/app/orders/{order_id}",
                    get_json(f"/app/orders/{order_id}", headers=app_headers),
                    TypeAdapter(OrderDetailResponse),
                )
            )
            checks.append(
                (
                    f"/app/orders/{order_id}/status",
                    get_json(f"/app/orders/{order_id}/status", headers=app_headers),
                    TypeAdapter(OrderStatusResponse),
                )
            )
            checks.append(
                (
                    f"/app/orders/{order_id}/relay-history",
                    get_json(f"/app/orders/{order_id}/relay-history", headers=app_headers),
                    TypeAdapter(RelayHistoryResponse),
                )
            )

        if first_dropoff_id:
            checks.append(
                (
                    f"/app/dropoffs/{first_dropoff_id}",
                    get_json(f"/app/dropoffs/{first_dropoff_id}", headers=app_headers),
                    TypeAdapter(DropoffDetailResponse),
                )
            )
            status_json = patch_json(
                f"/app/dropoffs/{first_dropoff_id}/status",
                {"status": "full"},
                headers=app_headers,
            )
            checks.append((f"/app/dropoffs/{first_dropoff_id}/status [PATCH]", status_json, TypeAdapter(DropoffStatusResponse)))
            _ = patch_json(
                f"/app/dropoffs/{first_dropoff_id}/status",
                {"status": "active"},
                headers=app_headers,
            )

        if first_restaurant:
            routing_json = get_json(
                "/app/routing/path",
                headers=app_headers,
                params={
                    "origin_lat": float(first_restaurant["lat"]),
                    "origin_lng": float(first_restaurant["lng"]),
                    "destination_lat": float(first_restaurant["lat"]) + 0.02,
                    "destination_lng": float(first_restaurant["lng"]) + 0.02,
                },
            )
            checks.append(("/app/routing/path", routing_json, TypeAdapter(RoutingResponse)))

        if first_zone_id:
            partner_reg = client.post(
                f"{base_url}/partner/register",
                json={
                    "name": "Contract Test Partner",
                    "phone": "+1-000-000-0000",
                    "zone_id": first_zone_id,
                    "city_id": city_id,
                },
            )
            if partner_reg.status_code != 200:
                raise RuntimeError(f"/partner/register returned {partner_reg.status_code}: {partner_reg.text[:300]}")
            partner_reg_json = partner_reg.json()
            checks.append(("/partner/register", partner_reg_json, TypeAdapter(PartnerRegisterResponse)))
            partner_headers = {"X-API-Key": partner_reg_json["api_key"]}

            checks.append(("/partner", get_json("/partner", headers=partner_headers), TypeAdapter(PartnerProfileResponse)))
            checks.append(
                (
                    "/partner/status",
                    patch_json("/partner/status", {"status": "available"}, headers=partner_headers),
                    TypeAdapter(PartnerStatusResponse),
                )
            )
            next_task_json = get_json("/partner/next-task", headers=partner_headers)
            checks.append(("/partner/next-task", next_task_json, TypeAdapter(NextTaskResponse)))
            checks.append(
                (
                    "/partner/task-history",
                    get_json("/partner/task-history", headers=partner_headers),
                    TypeAdapter(PartnerTaskHistoryResponse),
                )
            )

            task = next_task_json.get("task")
            if task and order_id and task.get("dropoff_id"):
                complete_resp = client.post(
                    f"{base_url}/partner/complete-task",
                    headers=partner_headers,
                    json={
                        "order_id": order_id,
                        "completed_dropoff_id": task["dropoff_id"],
                    },
                )
                if complete_resp.status_code == 200:
                    checks.append(
                        (
                            "/partner/complete-task",
                            complete_resp.json(),
                            TypeAdapter(CompleteTaskResponse),
                        )
                    )

        for endpoint, payload, adapter in checks:
            result = _validate(endpoint, payload, adapter)
            results.append(result)
            failures += 0 if result.ok else 1

    return results, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate API contract against response schemas")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    results, failures = run(args.base_url.rstrip("/"))

    print("\nContract Validation Results")
    print("-" * 40)
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        print(f"[{status}] {item.endpoint}")
        if item.detail and not item.ok:
            print(item.detail[:1500])
            print("-" * 40)
    print(f"Total validations: {len(results)}")
    print(f"Failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
