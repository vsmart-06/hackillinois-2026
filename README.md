# RelayRoute API

A plug-and-play relay delivery infrastructure API. Enables any quick commerce platform to implement zone-based relay delivery — where each partner operates within a small geographic zone, handing off packages at shared drop-off points rather than completing full end-to-end deliveries.

---

## Core Concepts

- **City** — A configured delivery market. Set up once; all subsequent calls reference it by `city_id`.
- **Zone** — A geographic sub-region of the city, partitioned by restaurant density.
- **Drop-off Point** — A physical handoff location on zone borders where packages are transferred between partners. Each point has a real-time capacity state.
- **Relay Chain** — The sequence of zones and drop-off points an order traverses from restaurant to destination, computed dynamically using Dijkstra's algorithm over a live-weighted graph.

---

## App-Facing Endpoints
*Called by the delivery platform's backend (e.g. Blinkit's servers)*

### City Setup

**`POST /app/setup`**
One-time setup for a city. Fetches restaurant locations via Google Maps, partitions the city into zones by density, and places drop-off points on zone borders. Returns the complete city topology.
```json
Request:  { city_name, grid_resolution?, dropoff_spacing_km?, dropoff_capacity? }
Response: { city_id, zones: [...], restaurants: [...], dropoff_points: [...] }
```

**`GET /app/setup/{city_id}`**
Returns the full topology for a previously configured city.

---

### Orders

**`POST /app/orders`**
Places a new order. Runs Dijkstra's on the current graph state — accounting for live traffic, box capacity, and partner availability — to compute the optimal relay chain.
```json
Request:  { city_id, restaurant_id, delivery_address }
Response: { order_id, relay_chain: [{ zone_id, dropoff_id, coords }], estimated_handoffs }
```

**`GET /app/orders/{order_id}/status`**
Returns current order state — which drop-off point it's at, which zone it's traversing, estimated remaining steps.

---

### Analytics

**`GET /app/zones/{zone_id}/load`**
Returns active order count and available partner count for a zone.

---

## Partner-Facing Endpoints
*Called by the delivery partner's mobile app*

### Partner Management

**`POST /partner/register`**
Registers a new delivery partner and assigns them to a zone.
```json
Request:  { name, phone, zone_id, city_id }
Response: { partner_id, zone: { id, boundaries, dropoff_points } }
```

**`PATCH /partner/{partner_id}/status`**
Updates partner availability: `available`, `carrying`, `offline`. Offline and carrying partners are excluded from routing or given penalty weights.

---

### Task Management

**`GET /partner/{partner_id}/next-task`**
Primary polling endpoint. Returns the partner's next action with coordinates.
```json
Response: {
  task_type: "pickup_restaurant" | "pickup_dropoff" | "deliver_dropoff",
  location: { lat, lng, address },
  order_id,
  instructions
}
```

**`POST /partner/{partner_id}/complete-task`**
Called when a partner completes a handoff. Increments the drop-off point's load, checks capacity, updates order state, and queues the next partner in the chain.
```json
Request:  { order_id, dropoff_point_id }
Response: { next_status, order_status, dropoff_status }
```

---

## Drop-off Point Management

**`PATCH /dropoff/{dropoff_id}/status`**
Manually override a drop-off point's status. Intended for admin use or IoT sensor integration. Disabled points are immediately removed from the routing graph.
```json
Request:  { status: "active" | "full" | "disabled" }
Response: { dropoff_id, status, affected_orders: [...] }
```

**`GET /dropoff/{dropoff_id}`**
Returns current state of a drop-off point — status, current load, capacity, and active orders passing through it.

---

## Routing (Inspectable)

**`GET /routing/path`**
Exposes the core routing algorithm. Runs Dijkstra's on the live graph — edge weights derived from real-time Google Maps traffic data, drop-off point capacity, and zone partner availability. Full/disabled boxes are pruned from the graph entirely before the algorithm runs.
```json
Request:  { city_id, origin: { lat, lng }, destination: { lat, lng } }
Response: { 
  relay_chain: [{ zone_id, dropoff_point_id, coords }], 
  total_handoffs,
  edge_weights: [{ from, to, weight, factors }]
}
```

The `edge_weights` field is purely for developer transparency — it lets consuming apps understand why a particular path was chosen.

---

## Authentication

All app-facing endpoints require an `X-API-Key` header, scoped to a specific city configuration. Partner-facing endpoints authenticate via `partner_id` bound to the same city. A key issued for Mumbai cannot place orders in Bangalore.