"""
RelayRoute API entrypoint.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from relayroute.routers import app_setup, app_zones, app_orders, app_dropoffs, app_partners, partner, routing

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
OPENAPI_TAGS = [
    {
        "name": "City Setup",
        "description": "Configure a city's zone topology, restaurant clusters, and drop-off point placement in a single call.",
    },
    {
        "name": "Zones",
        "description": "Query real-time zone state including active partners, order load, and geographic boundaries.",
    },
    {
        "name": "Orders",
        "description": "Place orders and track their progress as they move through the relay chain hop by hop.",
    },
    {
        "name": "Drop-off Points",
        "description": "Monitor and manage the physical handoff boxes that connect zones in the relay network.",
    },
    {
        "name": "Partner",
        "description": "Register delivery partners, manage their availability, and dispatch tasks within their assigned zone.",
    },
    {
        "name": "Task Management",
        "description": "Dispatch and complete pickup and drop-off tasks that move packages through the relay chain.",
    },
    {
        "name": "Routing",
        "description": "Inspect the live Dijkstra path computation with full edge weight transparency for any origin-destination pair.",
    },
]

"""
RelayRoute is a plug-and-play relay delivery infrastructure API built for quick commerce platforms. Instead of a single delivery partner completing an end-to-end journey, RelayRoute divides cities into density-based zones and routes packages through a chain of partners — each operating only within their local zone, handing off at shared drop-off points.

The API handles all zone partitioning, drop-off placement, dynamic path computation, and partner dispatch out of the box. Platforms integrate once and get a fully managed relay logistics layer. Partners interact through a separate authenticated surface that tells them exactly where to go and what to do at each step.

To get started: call POST /app/setup with a city name to generate your zone topology and receive your API key. All subsequent requests use that key to place orders, manage partners, and monitor live delivery state.
"""

app = FastAPI(
    title="RelayRoute API",
    description=(
        "RelayRoute is a plug-and-play relay delivery infrastructure API built for quick commerce platforms. Instead of a single delivery partner completing an end-to-end journey, RelayRoute divides cities into density-based zones and routes packages through a chain of partners — each operating only within their local zone, handing off at shared drop-off points.\n\nThe API handles all zone partitioning, drop-off placement, dynamic path computation, and partner dispatch out of the box. Platforms integrate once and get a fully managed relay logistics layer. Partners interact through a separate authenticated surface that tells them exactly where to go and what to do at each step.\n\nTo get started: call POST /app/setup with a city name to generate your zone topology and receive your API key. All subsequent requests use that key to place orders, manage partners, and monitor live delivery state."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key required for authenticated app and partner endpoints.",
    }

    paths = schema.get("paths", {})
    for path, operations in paths.items():
        for method, operation in operations.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            if (path == "/app/setup" and method == "post") or (path == "/partner/register" and method == "post"):
                continue
            operation["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(app_setup.router, prefix="/app", tags=["City Setup"])
app.include_router(app_zones.router, prefix="/app", tags=["Zones"])
app.include_router(app_orders.router, prefix="/app", tags=["Orders"])
app.include_router(app_dropoffs.router, prefix="/app", tags=["Drop-off Points"])
app.include_router(app_partners.router, prefix="/partner", tags=["Partner"])
app.include_router(partner.router, prefix="/partner", tags=["Partner"])
app.include_router(partner.task_router, prefix="/partner", tags=["Task Management"])
app.include_router(routing.router, prefix="/app/routing", tags=["Routing"])


@app.get("/", include_in_schema=False)
def serve_ui():
    """Serve the map UI at the root."""
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        return {"message": "RelayRoute API", "docs": "/docs", "ui": "Not found (missing web/)"}
    return FileResponse(index_path)


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="ui-static")
