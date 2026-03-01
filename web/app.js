(function () {
  "use strict";

  const getBase = () => document.getElementById("apiUrl").value.replace(/\/$/, "");
  const getApiKey = () => document.getElementById("apiKey").value.trim();

  function apiHeaders() {
    const key = getApiKey();
    const headers = { "Content-Type": "application/json" };
    if (key) headers["X-API-Key"] = key;
    return headers;
  }

  async function apiFetch(path, options = {}) {
    const url = getBase() + path;
    const res = await fetch(url, {
      ...options,
      headers: { ...apiHeaders(), ...(options.headers || {}) },
    });
    const text = await res.text();
    if (!res.ok) {
      let detail = text;
      try {
        const j = JSON.parse(text);
        detail = j.detail?.detail || j.detail || text;
      } catch (_) {}
      if (res.status === 401 && (detail || "").toLowerCase().includes("api key")) {
        detail = "Missing or invalid API key. Run Setup city first — the key is filled in the API key field above. If you already set up a city, paste that key again.";
      }
      throw new Error(detail);
    }
    return text ? JSON.parse(text) : null;
  }

  function showResult(elId, message, type = "info") {
    const el = document.getElementById(elId);
    el.textContent = message;
    el.className = "result " + type;
  }

  // ----- Map state -----
  let map = null;
  let layerZones = null;
  let layerRestaurants = null;
  let layerDropoffs = null;
  let layerOrderPaths = null;
  let currentCityId = null;
  let restaurants = [];
  let dropoffs = [];
  let zones = [];

  function initMap() {
    if (map) return;
    map = L.map("map").setView([12.97, 77.59], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
    }).addTo(map);

    layerZones = L.layerGroup().addTo(map);
    layerRestaurants = L.layerGroup().addTo(map);
    layerDropoffs = L.layerGroup().addTo(map);
    layerOrderPaths = L.layerGroup().addTo(map);

    document.getElementById("layerZones").addEventListener("change", updateLayerVisibility);
    document.getElementById("layerRestaurants").addEventListener("change", updateLayerVisibility);
    document.getElementById("layerDropoffs").addEventListener("change", updateLayerVisibility);
    document.getElementById("layerOrders").addEventListener("change", updateLayerVisibility);

    document.getElementById("showApiKey").addEventListener("change", function () {
      document.getElementById("apiKey").type = this.checked ? "text" : "password";
    });
  }

  function updateLayerVisibility() {
    layerZones.getMap() && map.removeLayer(layerZones);
    layerRestaurants.getMap() && map.removeLayer(layerRestaurants);
    layerDropoffs.getMap() && map.removeLayer(layerDropoffs);
    layerOrderPaths.getMap() && map.removeLayer(layerOrderPaths);
    if (document.getElementById("layerZones").checked) map.addLayer(layerZones);
    if (document.getElementById("layerRestaurants").checked) map.addLayer(layerRestaurants);
    if (document.getElementById("layerDropoffs").checked) map.addLayer(layerDropoffs);
    if (document.getElementById("layerOrders").checked) map.addLayer(layerOrderPaths);
  }

  function clearMapData() {
    layerZones.clearLayers();
    layerRestaurants.clearLayers();
    layerDropoffs.clearLayers();
    layerOrderPaths.clearLayers();
  }

  function drawTopology(data) {
    clearMapData();
    zones = data.zones || [];
    restaurants = data.restaurants || [];
    dropoffs = data.dropoff_points || [];

    const bounds = [];

    zones.forEach((zone) => {
      const boundaries = zone.boundaries;
      if (!boundaries || !boundaries.coordinates || !boundaries.coordinates[0]) return;
      const geo = {
        type: "Feature",
        geometry: boundaries,
        properties: { name: zone.name },
      };
      const layer = L.geoJSON(geo, {
        style: {
          color: "#c45a3b",
          weight: 1.5,
          fillColor: "#e8a090",
          fillOpacity: 0.25,
        },
      });
      layer.eachLayer((l) => {
        l.addTo(layerZones);
        if (l.getBounds) bounds.push(l.getBounds());
      });
    });

    restaurants.forEach((r) => {
      const m = L.circleMarker([r.lat, r.lng], {
        radius: 6,
        fillColor: "#2e7d32",
        color: "#1b5e20",
        weight: 1,
        fillOpacity: 0.9,
      }).bindTooltip(r.name || r.id, { permanent: false });
      m.restaurantId = r.id;
      m.addTo(layerRestaurants);
      bounds.push(L.latLng(r.lat, r.lng));
    });

    dropoffs.forEach((d) => {
      const color = d.status === "full" ? "#c62828" : d.status === "disabled" ? "#9e9e9e" : "#1565c0";
      const m = L.circleMarker([d.lat, d.lng], {
        radius: 7,
        fillColor: color,
        color: "#0d47a1",
        weight: 1,
        fillOpacity: 0.9,
      }).bindTooltip(`Drop-off ${d.id} (${d.status}, ${d.current_load}/${d.capacity})`, { permanent: false });
      m.addTo(layerDropoffs);
      bounds.push(L.latLng(d.lat, d.lng));
    });

    const select = document.getElementById("restaurantSelect");
    select.innerHTML = "";
    restaurants.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.name || r.id;
      select.appendChild(opt);
    });
    if (restaurants.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "— No restaurants —";
      select.appendChild(opt);
    }

    if (bounds.length) {
      const flat = [];
      bounds.forEach((b) => {
        if (b.getSouthWest && b.getNorthEast) {
          flat.push(b.getSouthWest(), b.getNorthEast());
        } else {
          flat.push(b);
        }
      });
      map.fitBounds(L.latLngBounds(flat), { padding: [20, 20], maxZoom: 14 });
    }

    document.getElementById("mapStatus").textContent =
      `${data.city_name || "City"}: ${zones.length} zones, ${restaurants.length} restaurants, ${dropoffs.length} drop-offs`;
  }

  function drawRelayChain(relayChain, restaurantLatLng, deliveryLatLng) {
    layerOrderPaths.clearLayers();

    const points = [];
    if (restaurantLatLng) points.push(restaurantLatLng);
    (relayChain || []).forEach((step) => {
      const c = step.coords || step;
      const lat = c.lat ?? c[1];
      const lng = c.lng ?? c[0];
      if (lat != null && lng != null) points.push([lat, lng]);
    });
    if (deliveryLatLng) points.push(deliveryLatLng);

    if (points.length < 2) return;
    L.polyline(points, {
      color: "#c45a3b",
      weight: 4,
      opacity: 0.9,
      dashArray: "8,8",
    }).addTo(layerOrderPaths);

    document.getElementById("layerOrders").checked = true;
    updateLayerVisibility();
    if (!layerOrderPaths.getMap()) map.addLayer(layerOrderPaths);
  }

  // ----- Setup city -----
  document.getElementById("btnSetup").addEventListener("click", async () => {
    const cityName = document.getElementById("cityName").value.trim();
    if (!cityName) {
      showResult("setupResult", "Enter a city name.", "error");
      return;
    }
    showResult("setupResult", "Setting up city (may take 10–30 s)…", "info");
    try {
      const body = {
        city_name: cityName,
        epsilon_km: parseFloat(document.getElementById("epsilonKm").value) || 0.5,
        min_restaurants_per_zone: parseInt(document.getElementById("minRestaurants").value, 10) || 10,
        dropoff_spacing_km: parseFloat(document.getElementById("dropoffSpacing").value) || 0.3,
        dropoff_capacity: parseInt(document.getElementById("dropoffCapacity").value, 10) || 20,
      };
      const data = await apiFetch("/app/setup", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const key = data.api_key || "";
      document.getElementById("apiKey").value = key;
      currentCityId = data.city_id;
      showResult(
        "setupResult",
        "City created. API key saved in the field above — click Load topology to draw the map.",
        "success"
      );
    } catch (e) {
      showResult("setupResult", e.message || "Setup failed", "error");
    }
  });

  // ----- Load topology -----
  document.getElementById("btnLoad").addEventListener("click", async () => {
    if (!getApiKey()) {
      showResult("loadResult", "Set API key first (from setup or paste).", "error");
      return;
    }
    initMap();
    showResult("loadResult", "Loading…", "info");
    try {
      const data = await apiFetch("/app/setup");
      currentCityId = data.city_id;
      drawTopology(data);
      showResult("loadResult", `Loaded ${data.city_name}.`, "success");
    } catch (e) {
      showResult("loadResult", e.message || "Load failed", "error");
    }
  });

  // ----- Place order -----
  document.getElementById("btnPlaceOrder").addEventListener("click", async () => {
    const cityId = currentCityId;
    const apiKey = getApiKey();
    const restaurantId = document.getElementById("restaurantSelect").value;
    const deliveryAddress = document.getElementById("deliveryAddress").value.trim();

    if (!apiKey || !cityId) {
      showResult("orderResult", "Load topology first so we have city_id and API key.", "error");
      return;
    }
    if (!restaurantId) {
      showResult("orderResult", "Select a restaurant.", "error");
      return;
    }
    if (!deliveryAddress) {
      showResult("orderResult", "Enter delivery address.", "error");
      return;
    }

    showResult("orderResult", "Placing order…", "info");
    try {
      const data = await apiFetch("/app/orders", {
        method: "POST",
        body: JSON.stringify({
          city_id: cityId,
          restaurant_id: restaurantId,
          delivery_address: deliveryAddress,
        }),
      });

      const rest = restaurants.find((r) => r.id === restaurantId);
      const restLatLng = rest ? [rest.lat, rest.lng] : null;
      let deliveryLatLng = null;
      try {
        const orderDetail = await apiFetch(`/app/orders/${data.order_id}`);
        deliveryLatLng = orderDetail.delivery_lat != null && orderDetail.delivery_lng != null
          ? [orderDetail.delivery_lat, orderDetail.delivery_lng]
          : null;
      } catch (_) {}

      drawRelayChain(data.relay_chain || [], restLatLng, deliveryLatLng);
      showResult(
        "orderResult",
        `Order ${data.order_id} placed. Handoffs: ${data.estimated_handoffs ?? "—"}. Path shown on map.`,
        "success"
      );
      document.getElementById("deliveryAddress").value = "";
      document.getElementById("btnRefreshOrders").click();
    } catch (e) {
      showResult("orderResult", e.message || "Place order failed", "error");
    }
  });

  // ----- Orders list -----
  document.getElementById("btnRefreshOrders").addEventListener("click", async () => {
    if (!getApiKey() || !currentCityId) return;
    const listEl = document.getElementById("ordersList");
    listEl.innerHTML = "";
    try {
      const orders = await apiFetch("/app/orders");
      if (!orders || orders.length === 0) {
        listEl.innerHTML = "<p class='hint'>No orders.</p>";
        return;
      }
      orders.forEach((o) => {
        const div = document.createElement("div");
        div.className = "order-item";
        div.innerHTML = `<span class="order-id">${o.order_id}</span><span class="order-status">${o.status}</span>`;
        div.addEventListener("click", async () => {
          document.querySelectorAll(".order-item").forEach((x) => x.classList.remove("active"));
          div.classList.add("active");
          try {
            const detail = await apiFetch(`/app/orders/${o.order_id}`);
            const chain = detail.relay_chain || [];
            const rest = restaurants.find((r) => r.id === detail.restaurant_id);
            const restLatLng = rest ? [rest.lat, rest.lng] : null;
            const deliveryLatLng =
              detail.delivery_lat != null && detail.delivery_lng != null
                ? [detail.delivery_lat, detail.delivery_lng]
                : null;
            drawRelayChain(chain, restLatLng, deliveryLatLng);
            document.getElementById("layerOrders").checked = true;
            updateLayerVisibility();
            if (!layerOrderPaths.getMap()) map.addLayer(layerOrderPaths);
          } catch (_) {}
        });
        listEl.appendChild(div);
      });
    } catch (_) {
      listEl.innerHTML = "<p class='result error'>Could not load orders.</p>";
    }
  });

  initMap();
})();
