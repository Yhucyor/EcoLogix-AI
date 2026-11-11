"""LightGBM Demand Forecasting, CVRPTW Green Routing & Financial/ESG Report Export Routes."""
import importlib
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend import config
from backend.database.connection import execute_query
from backend.dependencies import get_current_user, require_roles
from backend.services.carbon_service import get_esg_overview
from backend.services.financial_service import get_financial_overview, get_sensitivity_analysis
from backend.services.forecasting_service import (
    apply_po_recommendation,
    get_forecast_for_product,
    get_forecast_history,
    get_regional_demand_distribution,
    import_sales_history_csv,
)
from backend.services.inventory_service import get_all_products
from backend.services.routing_service import (
    get_pending_orders,
    get_road_route_geometry,
    get_saved_routes,
    optimize_100_points,
    optimize_routes_for_orders,
)
from backend.services.vehicle_service import get_vehicles_with_stats
from backend.utils.exporters import export_esg_pdf_bytes, export_financial_esg_excel_bytes

router = APIRouter(tags=["Forecasting, Routing & Reports"])


class ApplyPoReq(BaseModel):
    product_id: int
    quantity: int
    warehouse_id: int = 1


class ImportForecastCsvReq(BaseModel):
    product_id: int
    csv_text: str


class RouteOptReq(BaseModel):
    mode: str = "orders"
    order_ids: List[int] = []
    vehicle_id: Optional[int] = None
    enforce_time_window: bool = True
    save_to_db: bool = True
    scope_count: int = 100
    algorithm: str = "auto"
    multi_vehicle: bool = False


class RoadPoint(BaseModel):
    lat: float
    lng: float


class RoadGeometryReq(BaseModel):
    coordinates: List[RoadPoint] = []


@router.get("/api/forecast")
def api_forecast(product_id: int = 1, horizon_days: int = 30, save: bool = False, _: Dict[str, Any] = Depends(get_current_user)):
    prods = get_all_products()
    if not prods:
        raise HTTPException(status_code=404, detail="Không có sản phẩm.")
    target_id = product_id if any(p["id"] == product_id for p in prods) else prods[0]["id"]
    fc = get_forecast_for_product(target_id, horizon_days=horizon_days, save_history=save)
    hist_tail = fc["df_hist"].tail(20)
    fut_head = fc["df_fut"].head(min(30, horizon_days))
    return {
        "products": prods,
        "selected_product": fc["product"],
        "total_forecast": fc["total_forecast"],
        "avg_daily": fc["avg_daily"],
        "growth_pct": fc["growth_pct"],
        "safety_stock": fc["safety_stock"],
        "reorder_point": fc["reorder_point"],
        "current_qty": fc["current_qty"],
        "suggested_po": fc["suggested_po"],
        "accuracy_pct": fc["accuracy_pct"],
        "mape_pct": fc["mape_pct"],
        "model_name": fc["model_name"],
        "weekly_buckets": fc["weekly_buckets"],
        "hist_series": [{"date": d.strftime("%d/%m"), "actual": int(a)} for d, a in zip(hist_tail["date"], hist_tail["actual"])],
        "fut_series": [
            {"date": d.strftime("%d/%m"), "forecast": int(f), "lower": int(lo), "upper": int(hi)}
            for d, f, lo, hi in zip(fut_head["date"], fut_head["forecast"], fut_head["lower"], fut_head["upper"])
        ],
        "regions": get_regional_demand_distribution(),
        "forecast_history": get_forecast_history(limit=20),
    }


@router.post("/api/forecast/import-history")
def api_import_forecast_csv(req: ImportForecastCsvReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg, count = import_sales_history_csv(req.product_id, req.csv_text, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "imported_days": count}


@router.post("/api/forecast/apply-po")
def api_apply_po(req: ApplyPoReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    ok, msg = apply_po_recommendation(req.product_id, req.quantity, warehouse_id=req.warehouse_id, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.get("/api/routing")
def api_routing_init(_: Dict[str, Any] = Depends(get_current_user)):
    importlib.reload(config)
    pending = get_pending_orders()
    vehicles = get_vehicles_with_stats()
    default_ids = [o["id"] for o in pending[:6]]
    preview = optimize_routes_for_orders(default_ids, vehicle_id=vehicles[0]["id"] if vehicles else None, save_to_db=False) if default_ids else None
    return {
        "pending_orders": pending,
        "vehicles": vehicles,
        "saved_routes": get_saved_routes(limit=15),
        "preview": preview,
        "config": config.get_config_snapshot(),
    }


@router.post("/api/routing/optimize")
def api_routing_optimize(req: RouteOptReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager", "Dispatcher"))):
    if req.mode == "100points":
        res = optimize_100_points(scope_count=req.scope_count, enforce_avoidance=req.enforce_time_window)
        return {"ok": True, "mode": "100points", "result": res}
    if not req.order_ids:
        pending = get_pending_orders()
        req.order_ids = [o["id"] for o in pending[:6]]
    res = optimize_routes_for_orders(
        req.order_ids,
        vehicle_id=req.vehicle_id,
        enforce_time_window=req.enforce_time_window,
        save_to_db=req.save_to_db,
        user_id=user["id"],
        algorithm=req.algorithm,
        multi_vehicle=req.multi_vehicle,
    )
    if not res:
        raise HTTPException(status_code=400, detail="Không thể tối ưu vì thiếu đơn hàng hợp lệ.")
    return {"ok": True, "mode": "orders", "result": res, "saved_routes": get_saved_routes(limit=15)}


@router.post("/api/routing/road-geometry")
def api_routing_road_geometry(req: RoadGeometryReq):
    if len(req.coordinates) > 150:
        raise HTTPException(status_code=400, detail="Tối đa 150 điểm dừng mỗi tuyến đường.")
    return get_road_route_geometry([(pt.lat, pt.lng) for pt in req.coordinates])


@router.get("/api/reports")
def api_reports(_: Dict[str, Any] = Depends(get_current_user)):
    fin = get_financial_overview()
    esg = get_esg_overview()
    sens = get_sensitivity_analysis()
    return {**fin, **esg, "sensitivity": sens}


@router.get("/api/reports/export/pdf")
def api_export_pdf(_: Dict[str, Any] = Depends(get_current_user)):
    fin = get_financial_overview()
    esg = get_esg_overview()
    comp_rows = execute_query("SELECT name FROM companies ORDER BY id ASC LIMIT 1;")
    c_name = comp_rows[0]["name"] if comp_rows else "EcoLogix Logistics SME"
    pdf_bytes = export_esg_pdf_bytes({**fin, **esg}, company_name=c_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="EcoLogix_ESG_Financial_Report.pdf"'},
    )


@router.get("/api/reports/export/xlsx")
def api_export_xlsx(_: Dict[str, Any] = Depends(get_current_user)):
    fin = get_financial_overview()
    esg = get_esg_overview()
    xlsx_bytes = export_financial_esg_excel_bytes({**fin, **esg})
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="EcoLogix_Financial_ESG_Workbook.xlsx"'},
    )

