# RelayRoute API

RelayRoute is a relay-delivery backend for quick-commerce platforms. It sets up city topology (zones, restaurants, and drop-off points), computes inter-zone paths, and coordinates partner handoffs through authenticated app and partner APIs.

## Run Locally

```bash
# from project root
cp .env.example .env
pip install -e .
alembic upgrade head
python -m uvicorn relayroute.main:app --host 127.0.0.1 --port 8000
```

- Docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Demo UI: `http://127.0.0.1:8000/`

## Environment Variables

- `DATABASE_URL` (required)
- `GOOGLE_MAPS_API_KEY` or `GOOGLE_API_KEY` (required for setup/geocoding/travel time)
- `OPENAI_API_KEY` (optional, for zone reasoning text)

## Authentication

RelayRoute uses `X-API-Key` headers for both app and partner surfaces.

- **No auth required**
  - `POST /app/setup`
  - `POST /partner/register`
- **App API key required**
  - All other `/app/*` routes
- **Partner API key required**
  - All other `/partner/*` routes

```http
X-API-Key: your_api_key_here
```

## Endpoint Reference (Current)

### City Setup (`/app`)

- `POST /app/setup`  
  Initialize a city: discover restaurants, generate zones, place drop-off points, and return the first app API key.
- `GET /app/setup`  
  Get full topology for the city tied to the app API key.
- `GET /app/cities`  
  Return the single city account mapped to the app API key (1:1 mapping).

### Zones (`/app`)

- `GET /app/zones`  
  List all zones in the authenticated city.
- `GET /app/zones/{zone_id}`  
  Full zone detail: boundaries, restaurants, drop-offs, active partners, active orders.
- `GET /app/zones/{zone_id}/partners`  
  List partners assigned to the zone.
- `GET /app/zones/{zone_id}/dropoffs`  
  List drop-off points in the zone.
- `GET /app/zones/{zone_id}/orders`  
  List active orders currently traversing the zone.
- `GET /app/zones/{zone_id}/load`  
  Zone utilization and live load analytics.

### Orders (`/app`)

- `POST /app/orders`  
  Create an order, geocode destination, compute relay chain, and initialize relay dispatch.  
  If origin and destination resolve to the same zone, it becomes direct delivery (`relay_chain=[]`, `estimated_handoffs=0`).
- `GET /app/orders`  
  List city orders. Optional query: `status`.
- `GET /app/orders/{order_id}`  
  Full order payload including relay chain and current state.
- `GET /app/orders/{order_id}/status`  
  Compact status snapshot for polling.
- `GET /app/orders/{order_id}/relay-history`  
  Chronological task/handoff events for the order.

### Drop-off Points (`/app`)

- `GET /app/dropoffs`  
  List all drop-off points in the authenticated city.
- `GET /app/dropoffs/{dropoff_id}`  
  Get drop-off detail plus active orders that touch it.
- `PATCH /app/dropoffs/{dropoff_id}/status`  
  Set status (`active`, `full`, `disabled`) and return affected in-transit orders.

### Routing (`/app/routing`)

- `GET /app/routing/path`  
  Inspect computed relay path between origin and destination coordinates.  
  Query params: `origin_lat`, `origin_lng`, `destination_lat`, `destination_lng`.

### Partner (`/partner`)

- `POST /partner/register`  
  Register partner in a zone and return first partner API key.
- `GET /partner`  
  Get authenticated partner profile + current assignment.
- `PATCH /partner/status`  
  Update authenticated partner status (`available`, `carrying`, `offline`).

### Task Management (`/partner`)

- `GET /partner/next-task`  
  Poll next task for authenticated partner (`task` can be `null`).
- `POST /partner/complete-task`  
  Complete current handoff task and trigger relay progression.
- `GET /partner/task-history`  
  Get authenticated partner task history.

## Notes on Relay Behavior

- Zone path is computed via Dijkstra over zone adjacency.
- Relay checkpoints are chosen per hop in the **next zone** on the path.
- For each hop, checkpoint selection is based on proximity to the **current handoff location** (origin first, then previous checkpoint).
- Same-zone orders bypass relay and use direct delivery.
