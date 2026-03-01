"""Relay chain management + task queueing."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from relayroute.models import DropoffPoint, Order, Partner, Restaurant, TaskEvent


async def initialize_relay(order: Order, db: Session) -> None:
    """
    Initialize relay for a newly created order:
    1) keep status pending
    2) find first available partner in restaurant zone
    3) create first TaskEvent
    4) set partner carrying + current_order_id
    """
    restaurant = db.execute(
        select(Restaurant).where(Restaurant.id == order.restaurant_id)
    ).scalar_one_or_none()
    if restaurant is None:
        return

    partner = db.execute(
        select(Partner).where(
            Partner.city_id == order.city_id,
            Partner.zone_id == restaurant.zone_id,
            Partner.status == "available",
        )
    ).scalar_one_or_none()
    if partner is None:
        return

    partner.status = "carrying"
    partner.current_order_id = order.id
    db.add(
        TaskEvent(
            order_id=order.id,
            partner_id=partner.id,
            event="picked_up_from_restaurant",
            dropoff_id=None,
            timestamp=datetime.now(timezone.utc),
        )
    )


def _current_step_index(order: Order, completed_dropoff_id: str | None = None) -> int:
    chain = order.relay_chain or []
    if not chain:
        return -1
    if completed_dropoff_id:
        for i, step in enumerate(chain):
            if step.get("dropoff_point_id") == completed_dropoff_id:
                return i
    if order.current_dropoff_id:
        for i, step in enumerate(chain):
            if step.get("dropoff_point_id") == order.current_dropoff_id:
                return i
    return 0


async def advance_relay(
    order_id: str,
    completed_dropoff_id: str,
    partner_id: str,
    db: Session,
) -> dict:
    """
    Called when a partner completes a task:
    1. Log TaskEvent with timestamp
    2. Increment dropoff current_load; if load >= capacity, set status "full"
    3. Determine next step in relay_chain
    4. If more steps remain: find available partner in next zone, assign task
    5. If final step: mark order "delivered"
    6. Set completing partner status back to "available"
    Return updated order_status and dropoff_status
    """
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    partner = db.execute(select(Partner).where(Partner.id == partner_id)).scalar_one_or_none()
    if partner is None:
        raise ValueError(f"Partner {partner_id} not found")
    if partner.current_order_id != order_id:
        raise ValueError(f"Partner {partner_id} is not assigned to order {order_id}")

    now = datetime.now(timezone.utc)
    db.add(
        TaskEvent(
            order_id=order.id,
            partner_id=partner.id,
            event="dropped_at_dropoff",
            dropoff_id=completed_dropoff_id,
            timestamp=now,
        )
    )

    dropoff_status = "active"
    dropoff = db.execute(
        select(DropoffPoint).where(DropoffPoint.id == completed_dropoff_id)
    ).scalar_one_or_none()
    if dropoff is not None:
        dropoff.current_load = (dropoff.current_load or 0) + 1
        if dropoff.current_load >= dropoff.capacity:
            dropoff.status = "full"
        dropoff_status = dropoff.status

    idx = _current_step_index(order, completed_dropoff_id=completed_dropoff_id)
    chain = order.relay_chain or []

    # Completing partner always goes back to available after handoff.
    partner.status = "available"
    partner.current_order_id = None

    if idx >= len(chain) - 1:
        order.status = "delivered"
        order.remaining_handoffs = 0
        order.current_zone_id = None
        order.current_dropoff_id = None
        return {
            "order_status": order.status,
            "dropoff_status": dropoff_status,
            "next_partner_id": None,
        }

    next_step = chain[idx + 1]
    order.status = "in_transit"
    order.remaining_handoffs = max(0, (order.remaining_handoffs or 0) - 1)
    order.current_zone_id = next_step.get("zone_id")
    order.current_dropoff_id = next_step.get("dropoff_point_id")

    next_partner = db.execute(
        select(Partner).where(
            Partner.city_id == order.city_id,
            Partner.zone_id == order.current_zone_id,
            Partner.status == "available",
        )
    ).scalar_one_or_none()
    if next_partner is not None:
        next_partner.status = "carrying"
        next_partner.current_order_id = order.id
        db.add(
            TaskEvent(
                order_id=order.id,
                partner_id=next_partner.id,
                event="picked_up_from_dropoff",
                dropoff_id=completed_dropoff_id,
                timestamp=now,
            )
        )

    return {
        "order_status": order.status,
        "dropoff_status": dropoff_status,
        "next_partner_id": (next_partner.id if next_partner else None),
    }


def _build_next_task(order: Order, task_type: str = "deliver_dropoff") -> dict | None:
    chain = order.relay_chain or []
    if not chain:
        return None
    step = None
    if order.current_dropoff_id:
        for s in chain:
            if s.get("dropoff_point_id") == order.current_dropoff_id:
                step = s
                break
    if step is None:
        step = chain[0]
    return {
        "task_type": task_type,
        "instructions": (
            f"Move order {order.id} to drop-off {step.get('dropoff_point_id')} "
            f"in zone {step.get('zone_id')}."
        ),
        "order_id": order.id,
        "dropoff_id": step.get("dropoff_point_id"),
        "zone_id": step.get("zone_id"),
        "coords": step.get("coords"),
    }


async def get_next_task(partner_id: str, db: Session) -> dict | None:
    """
    Look up the partner's current_order_id.
    If carrying: return the next drop-off target from relay_chain.
    If available: check if any unassigned tasks exist in their zone.
    If none: return None.
    """
    partner = db.execute(select(Partner).where(Partner.id == partner_id)).scalar_one_or_none()
    if partner is None:
        return None

    if partner.status == "carrying" and partner.current_order_id:
        order = db.execute(
            select(Order).where(Order.id == partner.current_order_id)
        ).scalar_one_or_none()
        if order is None:
            return None
        return _build_next_task(order, task_type="deliver_dropoff")

    # Try to pick a waiting order in this partner's zone.
    candidates = db.execute(
        select(Order).where(
            Order.city_id == partner.city_id,
            Order.current_zone_id == partner.zone_id,
            Order.status.in_(["pending", "in_transit"]),
        )
    ).scalars().all()
    for order in candidates:
        assigned = db.execute(
            select(Partner).where(Partner.current_order_id == order.id, Partner.status == "carrying")
        ).scalar_one_or_none()
        if assigned is None:
            partner.status = "carrying"
            partner.current_order_id = order.id
            db.add(
                TaskEvent(
                    order_id=order.id,
                    partner_id=partner.id,
                    event="picked_up_from_dropoff",
                    dropoff_id=order.current_dropoff_id,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            return _build_next_task(order, task_type="pickup_dropoff")
    return None
