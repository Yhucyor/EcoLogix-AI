"""
EcoLogix AI - Unified FastAPI Application (`backend/main.py`)
Phục vụ Frontend SPA (`frontend/`) và cung cấp đầy đủ REST API nối tới SQLite, LightGBM, CVRPTW, 6 Agents & Reports.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.database.connection import execute_query
from backend.database.models import init_database
from backend.database.seed import seed_all
from backend.routers import ai, analytics, auth, dashboard, inventory, orders, partners, system, vehicles


def _ensure_bootstrap_data():
    init_database()
    try:
        rows = execute_query("SELECT COUNT(*) AS cnt FROM users;")
        if rows and int(rows[0]["cnt"]) == 0:
            seed_all()
    except Exception:
        pass


_ensure_bootstrap_data()

app = FastAPI(title="EcoLogix AI API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    dashboard.router,
    inventory.router,
    orders.router,
    vehicles.router,
    partners.router,
    analytics.router,
    ai.router,
    system.router,
):
    app.include_router(router)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
FRONTEND_INDEX = os.path.join(FRONTEND_DIR, "index.html")
FRONTEND_ASSETS = os.path.join(FRONTEND_DIR, "assets")
FRONTEND_COMPONENTS = os.path.join(FRONTEND_DIR, "components")
FRONTEND_PAGES = os.path.join(FRONTEND_DIR, "pages")

for mount_path, directory, mount_name in (
    ("/assets", FRONTEND_ASSETS, "assets"),
    ("/components", FRONTEND_COMPONENTS, "components"),
    ("/pages", FRONTEND_PAGES, "pages"),
):
    if os.path.isdir(directory):
        app.mount(mount_path, StaticFiles(directory=directory), name=mount_name)


def serve_webapp():
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


SPA_ROUTES = (
    "/",
    "/index.html",
    "/login",
    "/register",
    "/onboarding",
    "/dashboard",
    "/inventory",
    "/forecasting",
    "/orders",
    "/routing",
    "/vehicles",
    "/partners",
    "/ai-assistant",
    "/ai_assistant",
    "/reports",
    "/notifications",
    "/settings",
)
for _spa_path in SPA_ROUTES:
    app.add_api_route(_spa_path, serve_webapp, methods=["GET"], include_in_schema=False)


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    ico_path = os.path.join(FRONTEND_ASSETS, "favicon.ico")
    if os.path.isfile(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")

