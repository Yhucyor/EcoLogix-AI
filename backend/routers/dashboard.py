"""Health, Dashboard Overview, Global Search & Landing Contact Routes."""
import importlib
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend import config
from backend.database.connection import execute_query, rows_to_dicts
from backend.dependencies import get_current_user
from backend.services.carbon_service import get_esg_overview
from backend.services.email_service import send_contact_email
from backend.services.financial_service import get_financial_overview
from backend.services.inventory_service import get_inventory_metrics, get_inventory_status
from backend.utils.helpers import create_notification, log_activity

router = APIRouter(tags=["Dashboard & Public"])


class ContactReq(BaseModel):
    name: str
    contact: str
    need: str = "Dùng thử 14 ngày"
    message: str = ""
    source: str = "Đặt lịch Tư vấn & Dùng thử 1-1 / FAQ"


@router.get("/api/health")
def health():
    importlib.reload(config)
    return {"status": "ok", "config": config.get_config_snapshot()}


@router.get("/api/search")
def global_search(q: str = "", _: Dict[str, Any] = Depends(get_current_user)):
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


@router.post("/api/contact")
def submit_contact(req: ContactReq):
    if not req.name.strip() or not req.contact.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập họ tên và thông tin liên hệ.")
    create_notification(1, f"Yêu cầu tư vấn: {req.name}", f"{req.need} | {req.contact} | {req.message}", "info")
    email_res = send_contact_email(
        name=req.name,
        contact=req.contact,
        need=req.need,
        message=req.message,
        source=req.source,
    )
    log_activity(
        1,
        "LANDING_CONTACT",
        "notifications",
        None,
        f"Yêu cầu tư vấn từ {req.name} ({req.contact}) -> {email_res['recipient']} [{email_res['mode']}]",
    )
    msg = (
        f"Đã gửi email trực tiếp tới {email_res['recipient']} và ghi nhận yêu cầu tư vấn!"
        if email_res["email_sent"]
        else f"Đã ghi nhận yêu cầu tư vấn! Bấm mở Gmail/Mail để gửi tới {email_res['recipient']}."
    )
    return {
        "ok": True,
        "message": msg,
        "email_sent": email_res["email_sent"],
        "mode": email_res["mode"],
        "recipient": email_res["recipient"],
        "mailto_url": email_res["mailto_url"],
        "gmail_compose_url": email_res["gmail_compose_url"],
    }


@router.get("/api/dashboard")
def api_dashboard(_: Dict[str, Any] = Depends(get_current_user)):
    importlib.reload(config)
    fin = get_financial_overview()
    esg = get_esg_overview()
    inv = get_inventory_metrics()
    active_routes = rows_to_dicts(execute_query("SELECT * FROM routes ORDER BY id DESC LIMIT 3;"))
    map_routes = []
    for rt in active_routes:
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

