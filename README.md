# RelayRoute API

A plug-and-play relay delivery infrastructure API. Enables any quick commerce
platform to implement zone-based relay delivery — where each partner operates
within a small geographic zone, handing off packages at shared drop-off points
rather than completing full end-to-end deliveries.

---

## Core Concepts

- **City** — A configured delivery market. Set up once; all subsequent calls reference it by `city_id`.
- **Zone** — A geographic sub-region of the city, derived automatically via DBSCAN clustering on restaurant density. No need to specify zone count upfront.
- **Drop-off Point** — A physical handoff location on zone borders where packages are transferred between partners. Each point tracks real-time capacity state.
- **Relay Chain** — The sequence of zones and drop-off points an order traverses from restaurant to destination, computed dynamically using Dijkstra's algorithm over a live-weighted graph.

---

## Authentication

All app-facing endpoints require an `X-API-Key` header, scoped to a specific city configuration. Partner-facing endpoints authenticate via `partner_id` bound to the same city. A key issued for Mumbai cannot place orders in Bangalore.

```http
X-API-Key: your-api-key-here
```

---

## App-Facing Endpoints

> Called by the delivery platform's backend (e.g. Blinkit's servers)

---

### Cities

#### `POST /app/setup`

One-time setup for a city. Fetches restaurant locations via Google Maps, partitions the city into zones using DBSCAN clustering, and places drop-off points on zone borders. Returns the complete city topology along with an AI-generated explanation of the zone layout.

DBSCAN parameters allow operators to tune clustering to their city's density. Recommended defaults: `epsilon_km: 0.5` for metro cities (Mumbai, Bangalore), `epsilon_km: 1.5` for tier-2 cities (Nagpur, Jaipur).

**Request**
```json
{
  "city_name": "Bangalore",
  "epsilon_km": 0.5,
  "min_restaurants_per_zone": 10,
  "dropoff_spacing_km": 0.3,
  "dropoff_capacity": 20
}
```

**Response**
```json
{
  "city_id": "city_bangalore_01",
  "zones": [],
  "restaurants": [],
  "dropoff_points": [],
  "zone_reasoning": "Zone 3 covers Koramangala due to the highest restaurant density in south Bangalore."
}
```

---

#### `GET /app/setup/{city_id}`

Returns the full topology for a previously configured city.

---

#### `GET /app/cities`

Lists all cities configured under this API key.

**Response**
```json
{
  "cities": [
    {
      "city_id": "city_bangalore_01",
      "city_name": "Bangalore",
      "zone_count": 12,
      "active_partners": 340
    }
  ]
}
```

---

### Zones

#### `GET /app/zones?city_id={city_id}`

Lists all zones for a city with summary stats.

**Response**
```json
{
  "zones": [
    {
      "zone_id": "zone_01",
      "name": "Koramangala",
      "restaurant_count": 42,
      "active_partners": 8,
      "active_orders": 5
    }
  ]
}
```

---

#### `GET /app/zones/{zone_id}`

Returns full details for a zone — boundaries, restaurant list, drop-off points, active partners, and current order load.

---

#### `GET /app/zones/{zone_id}/partners`

Returns all partners currently assigned to a zone and their real-time statuses.

**Response**
```json
{
  "zone_id": "zone_01",
  "partners": [
    {
      "partner_id": "p_123",
      "name": "Arjun",
      "status": "available"
    }
  ]
}
```

---

#### `GET /app/zones/{zone_id}/dropoffs`

Returns all drop-off points in a zone with current capacity state.

---

#### `GET /app/zones/{zone_id}/orders`

Returns all active orders currently moving through a zone.

---

#### `GET /app/zones/{zone_id}/load`

Returns a real-time load snapshot — active order count and available partner count. Useful for dynamic pricing or load balancing decisions.

**Response**
```json
{
  "zone_id": "zone_01",
  "active_orders": 5,
  "available_partners": 3,
  "load_status": "moderate"
}
```

---

### Orders

#### `POST /app/orders`

Places a new order. Runs Dijkstra's algorithm on the current graph state — edge weights derived from live traffic data, drop-off box capacity, and zone partner availability — to compute the optimal relay chain.

**Request**
```json
{
  "city_id": "city_bangalore_01",
  "restaurant_id": "r_456",
  "delivery_address": "12 Indiranagar Main Rd, Bangalore"
}
```

**Response**
```json
{
  "order_id": "ord_789",
  "relay_chain": [
    {
      "zone_id": "zone_01",
      "dropoff_point_id": "dp_12",
      "coords": { "lat": 12.97, "lng": 77.64 }
    }
  ],
  "estimated_handoffs": 3
}
```

---

#### `GET /app/orders?city_id={city_id}&status={status}`

Lists all orders for a city. Filterable by `status`: `pending`, `in_transit`, `delivered`, `failed`.

---

#### `GET /app/orders/{order_id}/status`

Returns the current state of an order — which drop-off point it's at, which zone it's traversing, and estimated remaining steps.

**Response**
```json
{
  "order_id": "ord_789",
  "status": "in_transit",
  "current_dropoff": "dp_12",
  "current_zone": "zone_02",
  "remaining_handoffs": 2
}
```

---

#### `GET /app/orders/{order_id}/relay-history`

Returns the full log of every handoff on this order with timestamps. Useful for debugging, SLA tracking, and customer support.

**Response**
```json
{
  "order_id": "ord_789",
  "history": [
    {
      "event": "picked_up_from_restaurant",
      "partner_id": "p_123",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "event": "dropped_at_dropoff",
      "dropoff_id": "dp_12",
      "timestamp": "2024-01-15T10:38:00Z"
    }
  ]
}
```

---

### Drop-off Points

#### `GET /app/dropoffs?city_id={city_id}`

Returns all drop-off points for a city with current capacity state in a single call — useful for a full fleet snapshot without hitting individual endpoints.

---

#### `GET /dropoff/{dropoff_id}`

Returns current state of a drop-off point — status, current load, capacity, and active orders passing through it.

**Response**
```json
{
  "dropoff_id": "dp_12",
  "status": "active",
  "current_load": 14,
  "capacity": 20,
  "active_orders": ["ord_789", "ord_790"]
}
```

---

#### `PATCH /dropoff/{dropoff_id}/status`

Manually override a drop-off point's status. Intended for admin use or IoT sensor integration. Disabled points are immediately pruned from the routing graph and affected in-flight orders are surfaced for rerouting.

**Request**
```json
{
  "status": "active"
}
```

> Accepted values for `status`: `active`, `full`, `disabled`

**Response**
```json
{
  "dropoff_id": "dp_12",
  "status": "disabled",
  "affected_orders": ["ord_789"]
}
```

---

## Partner-Facing Endpoints

> Called by the delivery partner's mobile app

---

### Partner Management

#### `POST /partner/register`

Registers a new delivery partner and assigns them to a zone.

**Request**
```json
{
  "name": "Arjun Sharma",
  "phone": "+91-9876543210",
  "zone_id": "zone_01",
  "city_id": "city_bangalore_01"
}
```

**Response**
```json
{
  "partner_id": "p_123",
  "zone": {
    "id": "zone_01",
    "boundaries": [],
    "dropoff_points": []
  }
}
```

---

#### `GET /partner/{partner_id}`

Returns full partner profile — name, assigned zone, current status, and current task if carrying.

**Response**
```json
{
  "partner_id": "p_123",
  "name": "Arjun Sharma",
  "zone_id": "zone_01",
  "status": "carrying",
  "current_task": {
    "order_id": "ord_789",
    "destination": "dp_12"
  }
}
```

---

#### `PATCH /partner/{partner_id}/status`

Updates partner availability. Carrying and offline partners are excluded from new task assignment.

**Request**
```json
{
  "status": "available"
}
```

> Accepted values for `status`: `available`, `carrying`, `offline`

**Response**
```json
{
  "partner_id": "p_123",
  "status": "available"
}
```

---

### Task Management

#### `GET /partner/{partner_id}/next-task`

Primary polling endpoint for partner apps. Returns the next action with exact coordinates and instructions. Returns `null` for `task` if no tasks are currently available in the zone.

**Response**
```json
{
  "task_type": "pickup_restaurant",
  "location": {
    "lat": 12.97,
    "lng": 77.64,
    "address": "Meghana Foods, Koramangala"
  },
  "order_id": "ord_789",
  "instructions": "Collect order ord_789 and drop at Box dp_12 on 80 Feet Rd"
}
```

> Accepted values for `task_type`: `pickup_restaurant`, `pickup_dropoff`, `deliver_dropoff`

---

#### `POST /partner/{partner_id}/complete-task`

Called when a partner completes a handoff. Increments the drop-off point's load, checks capacity threshold, updates order state, and queues the next partner in the relay chain.

**Request**
```json
{
  "order_id": "ord_789",
  "dropoff_point_id": "dp_12"
}
```

**Response**
```json
{
  "next_status": "available",
  "order_status": "in_transit",
  "dropoff_status": "active"
}
```

---

#### `GET /partner/{partner_id}/task-history`

Returns a paginated log of all tasks completed by this partner.

**Response**
```json
{
  "partner_id": "p_123",
  "tasks": [
    {
      "order_id": "ord_789",
      "task_type": "pickup_restaurant",
      "completed_at": "2024-01-15T10:38:00Z"
    }
  ]
}
```

---

## Routing (Inspectable)

#### `GET /routing/path`

Exposes the core routing algorithm directly. Runs Dijkstra's algorithm on the live-weighted graph — edge weights derived from real-time Google Maps traffic data, drop-off point capacity, and zone partner availability. Full or disabled boxes are pruned from the graph before the algorithm runs.

The `edge_weights` field in the response is purely for developer transparency — it lets consuming apps understand why a particular path was chosen, aiding debugging and trust.

**Request**
```json
{
  "city_id": "city_bangalore_01",
  "origin": { "lat": 12.93, "lng": 77.61 },
  "destination": { "lat": 12.97, "lng": 77.64 }
}
```

**Response**
```json
{
  "relay_chain": [
    {
      "zone_id": "zone_01",
      "dropoff_point_id": "dp_12",
      "coords": { "lat": 12.95, "lng": 77.62 }
    }
  ],
  "total_handoffs": 3,
  "edge_weights": [
    {
      "from": "zone_01",
      "to": "zone_02",
      "weight": 4.2,
      "factors": {
        "traffic": 2.1,
        "capacity_penalty": 0.0,
        "partner_availability_penalty": 2.1
      }
    }
  ]
}
```
