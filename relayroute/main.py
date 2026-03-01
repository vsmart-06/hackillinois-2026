"""
RelayRoute API entrypoint.
Zone-based relay delivery infrastructure for quick commerce platforms.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from relayroute.routers import app_setup, app_zones, app_orders, app_dropoffs, app_partners, partner, routing

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="RelayRoute API",
    description="Zone-based relay delivery infrastructure for quick commerce platforms.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(app_setup.router, prefix="/app", tags=["City Setup"])
app.include_router(app_zones.router, prefix="/app", tags=["Zones"])
app.include_router(app_orders.router, prefix="/app", tags=["Orders"])
app.include_router(app_dropoffs.router, prefix="/app", tags=["Drop-off Points"])
app.include_router(app_partners.router, prefix="/partner", tags=["Partner Management"])
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
