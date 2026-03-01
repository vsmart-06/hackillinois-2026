"""
RelayRoute API entrypoint.
Zone-based relay delivery infrastructure for quick commerce platforms.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from relayroute.routers import app_setup, app_zones, app_orders, app_dropoffs, partner, routing

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
app.include_router(partner.router, prefix="/partner", tags=["Partner"])
app.include_router(routing.router, prefix="/routing", tags=["Routing"])
