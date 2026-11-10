"""
EcoLogix AI - Unified FastAPI Backend Server (Port 3000)
Phục vụ giao diện React SPA (`webapp/index.html`) và cung cấp đầy đủ REST API nối trực tiếp tới SQLite,
LightGBM Forecasting, CVRPTW Green Routing, 6-Agent Pipeline, OpenPyXL/ReportLab Exports và `config.py`.
"""
import importlib
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from database.connection import execute_query, execute_update, rows_to_dicts
from services.auth_service import (
    authenticate_user,
    register_user,
    verify_user_account,
    request_password_reset,
    reset_password,
    get_all_users,
    get_all_roles,
    update_user_role,
    update_user_profile,
    complete_onboarding,
)
from services.inventory_service import (
    get_all_warehouses,
    add_warehouse,
    get_all_products,
    add_product,
    update_product,
    delete_product,
    get_inventory_status,
    record_transaction,
    transfer_stock,
    get_transaction_history,
    get_inventory_metrics,
)
from services.order_service import (
    get_orders,
    get_order_stats,
    get_order_detail,
    create_order,
    update_order_status,
    delete_order,
)
from services.vehicle_service import (
    get_vehicles_with_stats,
    add_vehicle,
    update_vehicle,
    delete_vehicle,
)
from services.partner_service import (
    get_customers,
    get_customer_orders,
    add_customer,
    update_customer,
    delete_customer,
    get_suppliers,
    add_supplier,
    update_supplier_debt,
    delete_supplier,
)
from services.forecasting_service import (
    get_forecast_for_product,
    apply_po_recommendation,
    get_regional_demand_distribution,
    get_forecast_history,
)
from services.routing_service import (
    get_pending_orders,
    get_saved_routes,
    optimize_routes_for_orders,
    optimize_100_points,
)
from services.financial_service import get_financial_overview, get_sensitivity_analysis
from services.carbon_service import get_esg_overview
from services.ai_service import process_agent_query, get_conversation_messages
from utils.helpers import create_notification, log_activity
from utils.exporters import export_financial_esg_excel_bytes, export_esg_pdf_bytes

app = FastAPI(title="EcoLogix AI API", version="2.0.0")
WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "webapp")
WEBAPP_INDEX = os.path.join(WEBAPP_DIR, "index.html")
WEBAPP_ASSETS = os.path.join(WEBAPP_DIR, "assets")
WEBAPP_COMPONENTS = os.path.join(WEBAPP_DIR, "components")
WEBAPP_PAGES = os.path.join(WEBAPP_DIR, "pages")
for mount_path, directory, mount_name in (
    ("/assets", WEBAPP_ASSETS, "assets"),
    ("/components", WEBAPP_COMPONENTS, "components"),
    ("/pages", WEBAPP_PAGES, "pages"),
):
    if os.path.isdir(directory):
        app.mount(mount_path, StaticFiles(directory=directory), name=mount_name)


# ======================== PYDANTIC MODELS ========================
class LoginReq(BaseModel):
    email: str
    password: str


class RegisterReq(BaseModel):
    name: str
    email: str
    password: str
    phone: str = ""
    role: str = "Manager"


class VerifyReq(BaseModel):
    email: str
    otp_code: str


class ForgotReq(BaseModel):
    email: str


class ResetReq(BaseModel):
    email: str
    token: str
    new_password: str


class ContactReq(BaseModel):
    name: str
    contact: str
    need: str = "Dùng thử 14 ngày"
    message: str = ""


class OnboardingReq(BaseModel):
    company_name: str
    tax_code: str = "0318992211"
    address: str = "Khu Công Nghệ Cao, TP. Thủ Đức"
    city: str = "TP. Hồ Chí Minh"
    industry: str = "Phân phối hàng tiêu dùng (FMCG)"
    size: str = "Doanh nghiệp nhỏ (10 - 50 nhân viên)"
    warehouse_name: str = ""
    warehouse_code: str = ""
    warehouse_address: str = ""
    vehicle_name: str = ""
    vehicle_plate: str = ""
    vehicle_type: str = "Tải nhẹ đô thị"
    fuel_type: str = "Diesel"
    max_load_kg: int = 1500
    fuel_price: int = 23500
    cost_per_km: float = 3800.0
    user_id: int = 1


class ProductReq(BaseModel):
    sku: str
    name: str
    category: str = "Đồ uống"
    unit: str = "Thùng"
    unit_price: float
    weight_kg: float
    min_stock: int = 40
    max_stock: int = 300


class ProductUpdateReq(BaseModel):
    name: str
    category: str
    unit: str
    unit_price: float
    weight_kg: float
    min_stock: int = 40
    max_stock: int = 300


class WarehouseReq(BaseModel):
    name: str
    code: str
    address: str
    capacity_m3: float = 2500.0


class InventoryTxReq(BaseModel):
    product_id: int
    warehouse_id: int
    to_warehouse_id: Optional[int] = None
    trans_type: str  # IN, OUT, ADJUST, TRANSFER
    quantity: int
    note: str = ""


class OrderCreateReq(BaseModel):
    order_code: str
    customer_id: int
    warehouse_id: int
    time_window_start: str = "08:00"
    time_window_end: str = "11:30"
    product_id: Optional[int] = None
    quantity: int = 10
    shipping_fee: float = 180000.0


class OrderStatusReq(BaseModel):
    status: str


class VehicleReq(BaseModel):
    plate_number: str
    vehicle_name: str
    vehicle_type: str = "Tải nhẹ đô thị"
    max_load_kg: float = 1500.0
    fuel_type: str = "Diesel"
    fuel_consumption_per_100km: float = 11.5
    operational_cost_per_km: float = 3800.0
    status: str = "Available"


class CustomerReq(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    district: str = "Quận 1"
    province: str = "TP.HCM"
    customer_tier: str = "Standard"


class SupplierReq(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    products_supplied: str = ""
    debt_vnd: float = 0.0


class DebtUpdateReq(BaseModel):
    debt_vnd: float


class ApplyPoReq(BaseModel):
    product_id: int
    quantity: int
    warehouse_id: int = 1


class RouteOptReq(BaseModel):
    mode: str = "orders"  # 'orders' hoặc '100points'
    order_ids: List[int] = []
    vehicle_id: Optional[int] = None
    enforce_time_window: bool = True
    save_to_db: bool = True
    scope_count: int = 100


class AiChatReq(BaseModel):
    query: str
    user_id: int = 1


class ProfileUpdateReq(BaseModel):
    user_id: int = 1
    name: str
    phone: str = ""


class CompanyUpdateReq(BaseModel):
    name: str
    tax_code: str = ""
    phone: str = ""
    address: str = ""
    industry: str = ""


class RoleUpdateReq(BaseModel):
    role: str


class AiSettingsReq(BaseModel):
    mode: str = "Hybrid-Demo"
    api_key: str = ""


class LiveCodeReq(BaseModel):
    fuel_price: int
    carbon_tax: int
    max_load_kg: int = 1500
    restricted_start: str = "16:00"
    restricted_end: str = "18:00"


# ======================== SERVE FRONTEND & HEALTH ========================
def serve_webapp():
    return FileResponse(WEBAPP_INDEX, media_type="text/html")


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


@app.get("/favicon.ico")
def serve_favicon():
    ico_path = os.path.join(WEBAPP_ASSETS, "favicon.ico")
    if os.path.isfile(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/api/health")
def health():
    importlib.reload(config)
    return {"status": "ok", "config": config.get_config_snapshot()}


@app.get("/api/search")
def global_search(q: str = ""):
    kw = q.strip()
    if not kw:
        return {"results": []}
    like = f"%{kw}%"
    results = []
    for o in execute_query("SELECT id, order_code, status FROM orders WHERE order_code LIKE ? LIMIT 4;", (like,)):
        results.append({"type": "order", "label": f"Đơn {o['order_code']} ({o['status']})", "page": "orders"})
    for p in execute_query("SELECT id, sku, name FROM products WHERE sku LIKE ? OR name LIKE ? LIMIT 4;", (like, like)):
        results.append({"type": "product", "label": f"{p['sku']} - {p['name']}", "page": "inventory"})
    for v in execute_query("SELECT id, plate_number, vehicle_name FROM vehicles WHERE plate_number LIKE ? OR vehicle_name LIKE ? LIMIT 4;", (like, like)):
        results.append({"type": "vehicle", "label": f"Xe {v['plate_number']} ({v['vehicle_name']})", "page": "vehicles"})
    for c in execute_query("SELECT id, name, province FROM customers WHERE name LIKE ? LIMIT 4;", (like,)):
        results.append({"type": "customer", "label": f"KH: {c['name']} ({c['province']})", "page": "partners"})
    return {"results": results}


@app.post("/api/contact")
def submit_contact(req: ContactReq):
    if not req.name.strip() or not req.contact.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập họ tên và thông tin liên hệ.")
    create_notification(1, f"Yêu cầu tư vấn: {req.name}", f"{req.need} | {req.contact} | {req.message}", "info")
    log_activity(1, "LANDING_CONTACT", "notifications", None, f"Yêu cầu tư vấn từ {req.name} ({req.contact})")
    return {"ok": True, "message": "Đã ghi nhận yêu cầu tư vấn! Đội ngũ EcoLogix AI sẽ liên hệ bạn sớm nhất."}


# ======================== AUTHENTICATION & ONBOARDING ========================
@app.post("/api/auth/login")
def api_login(req: LoginReq):
    ok, user_safe, msg = authenticate_user(req.email, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return {"ok": True, "user": user_safe, "message": msg}


@app.post("/api/auth/register")
def api_register(req: RegisterReq):
    ok, msg, otp = register_user(req.name, req.email, req.password, req.phone, req.role)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "demo_otp": otp}


@app.post("/api/auth/verify")
def api_verify(req: VerifyReq):
    ok, msg = verify_user_account(req.email, req.otp_code)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/auth/forgot")
def api_forgot(req: ForgotReq):
    ok, msg, token = request_password_reset(req.email)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"ok": True, "message": msg, "demo_token": token}


@app.post("/api/auth/reset")
def api_reset(req: ResetReq):
    ok, msg = reset_password(req.email, req.token, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/onboarding")
def api_onboarding(req: OnboardingReq):
    ok, msg, res = complete_onboarding(req.model_dump(), user_id=req.user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "data": res}


# ======================== DASHBOARD ========================
@app.get("/api/dashboard")
def api_dashboard():
    importlib.reload(config)
    fin = get_financial_overview()
    esg = get_esg_overview()
    inv = get_inventory_metrics()
    saved_routes = get_saved_routes(limit=3)
    map_routes = []
    for rt in saved_routes:
        stops = rows_to_dicts(execute_query(
            "SELECT lat, lng, address, arrival_time FROM route_stops WHERE route_id = ? ORDER BY stop_sequence ASC;",
            (rt["id"],),
        ))
        map_routes.append({**rt, "stops": stops})

    low_items = [r for r in get_inventory_status() if r["quantity"] <= r["safety_stock"]]
    logs = rows_to_dicts(execute_query("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 6;"))
    unread_rows = execute_query("SELECT COUNT(*) as cnt FROM notifications WHERE is_read = 0;")
    comp_rows = rows_to_dicts(execute_query("SELECT name FROM companies ORDER BY id ASC LIMIT 1;"))

    return {
        "financial": fin["financial_summary"],
        "monthly_financial": fin["monthly_financial"],
        "cost_breakdown": fin["cost_breakdown"],
        "esg": esg["esg_summary"],
        "esg_history": esg["esg_history"],
        "inventory": inv,
        "low_stock_items": low_items[:5],
        "depot": config.DEPOT_LOCATION,
        "map_routes": map_routes,
        "activity_logs": logs,
        "unread_notifications": unread_rows[0]["cnt"] if unread_rows else 0,
        "company_name": comp_rows[0]["name"] if comp_rows else "EcoLogix Logistics",
        "config": config.get_config_snapshot(),
    }


# ======================== INVENTORY & WAREHOUSES ========================
@app.get("/api/inventory")
def api_inventory(warehouse_id: Optional[int] = None, search: str = ""):
    return {
        "warehouses": get_all_warehouses(),
        "products": get_all_products(),
        "inventory": get_inventory_status(warehouse_id=warehouse_id, search=search),
        "transactions": get_transaction_history(limit=50),
        "metrics": get_inventory_metrics(),
    }


@app.post("/api/inventory/products")
def api_add_product(req: ProductReq):
    ok, msg = add_product(1, req.sku, req.name, req.category, req.unit, req.unit_price, req.weight_kg, req.min_stock, req.max_stock)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.put("/api/inventory/products/{product_id}")
def api_update_product(product_id: int, req: ProductUpdateReq):
    ok, msg = update_product(product_id, req.name, req.category, req.unit, req.unit_price, req.weight_kg, req.min_stock, req.max_stock)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.delete("/api/inventory/products/{product_id}")
def api_delete_product(product_id: int):
    ok, msg = delete_product(product_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/inventory/warehouses")
def api_add_warehouse(req: WarehouseReq):
    ok, msg = add_warehouse(req.name, req.code, req.address, req.capacity_m3)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/inventory/transactions")
def api_inventory_tx(req: InventoryTxReq):
    if req.trans_type == "TRANSFER":
        if not req.to_warehouse_id:
            raise HTTPException(status_code=400, detail="Thiếu kho đích để điều chuyển.")
        ok, msg = transfer_stock(req.product_id, req.warehouse_id, req.to_warehouse_id, req.quantity, req.note)
    else:
        ok, msg = record_transaction(req.product_id, req.warehouse_id, req.trans_type, req.quantity, req.note)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


# ======================== ORDERS ========================
@app.get("/api/orders")
def api_orders(status: str = "ALL", province: str = "ALL", search: str = ""):
    return {
        "orders": get_orders(status=status, province=province, search=search, limit=200),
        "stats": get_order_stats(),
        "customers": get_customers(),
        "warehouses": get_all_warehouses(),
        "products": get_all_products(),
    }


@app.get("/api/orders/{order_id}")
def api_order_detail(order_id: int):
    detail = get_order_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return detail


@app.post("/api/orders")
def api_create_order(req: OrderCreateReq):
    items = [{"product_id": req.product_id, "quantity": req.quantity}] if req.product_id else []
    ok, msg, oid = create_order(
        order_code=req.order_code,
        customer_id=req.customer_id,
        warehouse_id=req.warehouse_id,
        time_window_start=req.time_window_start,
        time_window_end=req.time_window_end,
        items=items,
        shipping_fee=req.shipping_fee,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "order_id": oid}


@app.patch("/api/orders/{order_id}/status")
def api_order_status(order_id: int, req: OrderStatusReq):
    ok, msg = update_order_status(order_id, req.status)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.delete("/api/orders/{order_id}")
def api_delete_order(order_id: int):
    ok, msg = delete_order(order_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


# ======================== VEHICLES ========================
@app.get("/api/vehicles")
def api_vehicles():
    return {"vehicles": get_vehicles_with_stats()}


@app.post("/api/vehicles")
def api_add_vehicle(req: VehicleReq):
    ok, msg = add_vehicle(
        req.plate_number, req.vehicle_name, req.vehicle_type,
        req.max_load_kg, req.fuel_type, req.fuel_consumption_per_100km, req.operational_cost_per_km,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.put("/api/vehicles/{vehicle_id}")
def api_update_vehicle(vehicle_id: int, req: VehicleReq):
    ok, msg = update_vehicle(
        vehicle_id, req.vehicle_name, req.vehicle_type, req.max_load_kg,
        req.fuel_type, req.fuel_consumption_per_100km, req.operational_cost_per_km, req.status,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.delete("/api/vehicles/{vehicle_id}")
def api_delete_vehicle(vehicle_id: int):
    ok, msg = delete_vehicle(vehicle_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


# ======================== CUSTOMERS & SUPPLIERS ========================
@app.get("/api/partners")
def api_partners(search: str = "", tier: str = "ALL"):
    return {
        "customers": get_customers(search=search, tier=tier),
        "suppliers": get_suppliers(search=search),
    }


@app.get("/api/partners/customers/{customer_id}/orders")
def api_customer_orders(customer_id: int):
    return {"orders": get_customer_orders(customer_id)}


@app.post("/api/partners/customers")
def api_add_customer(req: CustomerReq):
    ok, msg = add_customer(req.name, req.phone, req.email, req.address, req.district, req.province, req.customer_tier)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.put("/api/partners/customers/{customer_id}")
def api_update_customer(customer_id: int, req: CustomerReq):
    ok, msg = update_customer(customer_id, req.name, req.phone, req.email, req.address, req.district, req.province, req.customer_tier)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.delete("/api/partners/customers/{customer_id}")
def api_delete_customer(customer_id: int):
    ok, msg = delete_customer(customer_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/partners/suppliers")
def api_add_supplier(req: SupplierReq):
    ok, msg = add_supplier(req.name, req.phone, req.email, req.address, req.products_supplied, req.debt_vnd)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.patch("/api/partners/suppliers/{supplier_id}/debt")
def api_update_debt(supplier_id: int, req: DebtUpdateReq):
    ok, msg = update_supplier_debt(supplier_id, req.debt_vnd)
    return {"ok": ok, "message": msg}


@app.delete("/api/partners/suppliers/{supplier_id}")
def api_delete_supplier(supplier_id: int):
    ok, msg = delete_supplier(supplier_id)
    return {"ok": ok, "message": msg}


# ======================== FORECASTING ========================
@app.get("/api/forecast")
def api_forecast(product_id: int = 1, horizon_days: int = 30, save: bool = False):
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


@app.post("/api/forecast/apply-po")
def api_apply_po(req: ApplyPoReq):
    ok, msg = apply_po_recommendation(req.product_id, req.quantity, warehouse_id=req.warehouse_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


# ======================== GREEN ROUTING ========================
@app.get("/api/routing")
def api_routing_init():
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


@app.post("/api/routing/optimize")
def api_routing_optimize(req: RouteOptReq):
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
    )
    if not res:
        raise HTTPException(status_code=400, detail="Không thể tối ưu vì thiếu đơn hàng hợp lệ.")
    return {"ok": True, "mode": "orders", "result": res, "saved_routes": get_saved_routes(limit=15)}


# ======================== AI MULTI-AGENT ========================
@app.get("/api/ai/messages")
def api_ai_messages(user_id: int = 1):
    return {"messages": get_conversation_messages(user_id=user_id)}


@app.post("/api/ai/chat")
def api_ai_chat(req: AiChatReq):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    trace, reply, action = process_agent_query(req.query, user_id=req.user_id, save_to_db=True)
    return {
        "ok": True,
        "trace": trace,
        "reply": reply,
        "action": action,
        "messages": get_conversation_messages(user_id=req.user_id),
    }


# ======================== REPORTS & REAL EXPORTS ========================
@app.get("/api/reports")
def api_reports():
    fin = get_financial_overview()
    esg = get_esg_overview()
    sens = get_sensitivity_analysis()
    return {**fin, **esg, "sensitivity": sens}


@app.get("/api/reports/export/pdf")
def api_export_pdf():
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


@app.get("/api/reports/export/xlsx")
def api_export_xlsx():
    fin = get_financial_overview()
    esg = get_esg_overview()
    xlsx_bytes = export_financial_esg_excel_bytes({**fin, **esg})
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="EcoLogix_Financial_ESG_Workbook.xlsx"'},
    )


# ======================== NOTIFICATIONS ========================
@app.get("/api/notifications")
def api_notifications(notif_type: str = "ALL", unread_only: bool = False):
    query = "SELECT * FROM notifications WHERE 1=1"
    params = []
    if notif_type != "ALL":
        query += " AND type = ?"
        params.append(notif_type)
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY id DESC;"
    return {"notifications": rows_to_dicts(execute_query(query, tuple(params)))}


@app.post("/api/notifications/read-all")
def api_notif_read_all():
    execute_update("UPDATE notifications SET is_read = 1;")
    return {"ok": True}


@app.post("/api/notifications/{notif_id}/read")
def api_notif_read_one(notif_id: int):
    execute_update("UPDATE notifications SET is_read = 1 WHERE id = ?;", (notif_id,))
    return {"ok": True}


# ======================== SETTINGS & LIVE-CODE ========================
@app.get("/api/settings")
def api_settings(user_id: int = 1):
    importlib.reload(config)
    u_rows = rows_to_dicts(execute_query("SELECT id, name, email, role, phone, avatar_url FROM users WHERE id = ?;", (user_id,)))
    c_rows = rows_to_dicts(execute_query("SELECT * FROM companies ORDER BY id ASC LIMIT 1;"))
    sys_rows = rows_to_dicts(execute_query("SELECT setting_key, setting_value FROM system_settings WHERE company_id = 1;"))
    sys_map = {r["setting_key"]: r["setting_value"] for r in sys_rows}
    logs = rows_to_dicts(execute_query("SELECT a.*, u.name as user_name FROM activity_logs a LEFT JOIN users u ON a.user_id = u.id ORDER BY a.id DESC LIMIT 30;"))
    return {
        "user": u_rows[0] if u_rows else None,
        "company": c_rows[0] if c_rows else None,
        "users": get_all_users(),
        "roles": get_all_roles(),
        "ai_config": {
            "mode": sys_map.get("AI_PROVIDER_MODE", "Hybrid-Demo"),
            "has_api_key": bool((sys_map.get("LLM_API_KEY") or "").strip()),
        },
        "config": config.get_config_snapshot(),
        "sensitivity": get_sensitivity_analysis(),
        "activity_logs": logs,
    }


@app.put("/api/settings/profile")
def api_settings_profile(req: ProfileUpdateReq):
    ok, msg = update_user_profile(req.user_id, req.name, req.phone)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.put("/api/settings/company")
def api_settings_company(req: CompanyUpdateReq):
    c_rows = execute_query("SELECT id FROM companies ORDER BY id ASC LIMIT 1;")
    cid = c_rows[0]["id"] if c_rows else 1
    execute_update(
        "UPDATE companies SET name = ?, tax_code = ?, phone = ?, address = ?, industry = ? WHERE id = ?;",
        (req.name.strip(), req.tax_code.strip(), req.phone.strip(), req.address.strip(), req.industry.strip(), cid),
    )
    log_activity(1, "UPDATE_COMPANY", "companies", cid, f"Cập nhật doanh nghiệp {req.name}")
    return {"ok": True, "message": "Đã lưu thông tin doanh nghiệp vào SQLite!"}


@app.put("/api/settings/rbac/{target_user_id}")
def api_settings_rbac(target_user_id: int, req: RoleUpdateReq):
    update_user_role(target_user_id, req.role)
    return {"ok": True, "message": f"Đã cập nhật vai trò thành {req.role}!"}


@app.put("/api/settings/ai")
def api_settings_ai(req: AiSettingsReq):
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = 1 AND setting_key = 'AI_PROVIDER_MODE';", (req.mode,))
    if req.api_key:
        execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = 1 AND setting_key = 'LLM_API_KEY';", (req.api_key,))
    log_activity(1, "UPDATE_AI_CONFIG", "system_settings", 1, f"Đổi chế độ AI: {req.mode}")
    return {"ok": True, "message": "Đã cập nhật cấu hình AI!"}


@app.post("/api/settings/live-code")
def api_settings_live_code(req: LiveCodeReq):
    snap = config.save_live_config(
        req.fuel_price, req.carbon_tax, req.max_load_kg, req.restricted_start, req.restricted_end
    )
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = 1 AND setting_key = 'FUEL_PRICE_PER_LITER';", (str(req.fuel_price),))
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = 1 AND setting_key = 'CARBON_TAX_RATE';", (str(req.carbon_tax),))
    log_activity(1, "LIVE_CODE_UPDATE", "config.py", None, f"Fuel={req.fuel_price}, CarbonTax={req.carbon_tax}, Window={req.restricted_start}-{req.restricted_end}")
    return {
        "ok": True,
        "message": "Đã ghi trực tiếp tham số mới vào config.py & tính lại toàn bộ hệ thống!",
        "config": snap,
        "sensitivity": get_sensitivity_analysis(),
    }

