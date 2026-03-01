# RelayRoute Map UI

A simple real-time UI for the RelayRoute API: map view with zones, restaurants, drop-offs, and order relay chains.

## How to run

1. Start the API (from project root):
   ```bash
   uvicorn relayroute.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Open **http://localhost:8000/** in a browser. The UI is served from the same server.

If the API runs elsewhere, set **API base URL** in the sidebar (e.g. `http://localhost:8000`) and use the UI from any static host (e.g. open `index.html` with `file://` or another HTTP server). CORS is enabled on the API.

## Inputs and flow

| Input / action | Purpose |
|----------------|--------|
| **API base URL** | Backend base (default `http://localhost:8000`). |
| **API key** | Set after **Setup city** or paste an existing key. Used for Load topology and Place order. |
| **Setup city** | One-time: city name, DBSCAN params (ε km, min restaurants/zone), drop-off spacing and capacity. Calls `POST /app/setup`. Copy the returned API key into the **API key** field. |
| **Load topology** | Fetches zones (with boundaries), restaurants, and drop-offs via `GET /app/setup` and draws them on the map. |
| **Map layers** | Toggle Zones (polygons), Restaurants (green), Drop-offs (blue/full/disabled), Order paths (relay chain polyline). |
| **Place order** | Pick a restaurant (dropdown from loaded topology), enter delivery address, then **Place order**. Calls `POST /app/orders` and draws the relay chain on the map. |
| **Orders** | **Refresh orders** lists orders; click one to show its relay path on the map. |

## Map behaviour

- **Zones**: GeoJSON polygons (orange outline, light fill).
- **Restaurants**: Green circle markers; tooltip shows name.
- **Drop-offs**: Blue (active), red (full), grey (disabled); tooltip shows load/capacity.
- **Order path**: Dashed orange polyline from restaurant → relay chain drop-offs → delivery (if available).

No build step: plain HTML, CSS, and JS with Leaflet from CDN.
