"""Notifications, System Settings, RBAC & Live-Code Routes."""
import importlib
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend import config
from backend.database.connection import execute_query, execute_update, rows_to_dicts
from backend.dependencies import get_current_user, require_roles
from backend.services.auth_service import (
    get_all_roles,
    get_all_users,
    update_user_profile,
    update_user_role,
)
from backend.services.financial_service import get_sensitivity_analysis
from backend.utils.helpers import log_activity

router = APIRouter(tags=["Notifications & Settings"])


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


@router.get("/api/notifications")
def api_notifications(notif_type: str = "ALL", unread_only: bool = False, user: Dict[str, Any] = Depends(get_current_user)):
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params = [user["id"]]
    if notif_type != "ALL":
        query += " AND type = ?"
        params.append(notif_type)
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY id DESC;"
    return {"notifications": rows_to_dicts(execute_query(query, tuple(params)))}


@router.post("/api/notifications/read-all")
def api_notif_read_all(user: Dict[str, Any] = Depends(get_current_user)):
    execute_update("UPDATE notifications SET is_read = 1 WHERE user_id = ?;", (user["id"],))
    return {"ok": True}


@router.post("/api/notifications/{notif_id}/read")
def api_notif_read_one(notif_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    execute_update("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?;", (notif_id, user["id"]))
    return {"ok": True}


@router.get("/api/settings")
def api_settings(user_id: int = 1, current_user: Dict[str, Any] = Depends(get_current_user)):
    importlib.reload(config)
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else user_id
    company_id = current_user.get("company_id") or 1
    u_rows = rows_to_dicts(execute_query("SELECT id, name, email, role, phone, avatar_url FROM users WHERE id = ?;", (target_uid,)))
    c_rows = rows_to_dicts(execute_query("SELECT * FROM companies WHERE id = ?;", (company_id,)))
    sys_rows = rows_to_dicts(execute_query("SELECT setting_key, setting_value FROM system_settings WHERE company_id = ?;", (company_id,)))
    sys_map = {r["setting_key"]: r["setting_value"] for r in sys_rows}
    raw_key = (sys_map.get("LLM_API_KEY") or "").strip()
    masked = f"{raw_key[:4]}••••{raw_key[-4:]}" if len(raw_key) > 8 else ("••••••••" if raw_key else "")
    logs = rows_to_dicts(execute_query("""
    SELECT a.*, u.name as user_name
    FROM activity_logs a
    JOIN users u ON a.user_id = u.id
    WHERE u.company_id = ?
    ORDER BY a.id DESC LIMIT 30;
    """, (company_id,)))
    return {
        "user": u_rows[0] if u_rows else None,
        "company": c_rows[0] if c_rows else None,
        "users": get_all_users(company_id=company_id),
        "roles": get_all_roles(),
        "ai_config": {
            "mode": sys_map.get("AI_PROVIDER_MODE", "Hybrid-Demo"),
            "has_api_key": bool(raw_key),
            "api_key_masked": masked,
        },
        "config": config.get_config_snapshot(),
        "sensitivity": get_sensitivity_analysis(),
        "activity_logs": logs,
    }


@router.put("/api/settings/profile")
def api_settings_profile(req: ProfileUpdateReq, current_user: Dict[str, Any] = Depends(get_current_user)):
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else req.user_id
    ok, msg = update_user_profile(target_uid, req.name, req.phone)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.put("/api/settings/company")
def api_settings_company(req: CompanyUpdateReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    cid = user.get("company_id") or 1
    execute_update(
        "UPDATE companies SET name = ?, tax_code = ?, phone = ?, address = ?, industry = ? WHERE id = ?;",
        (req.name.strip(), req.tax_code.strip(), req.phone.strip(), req.address.strip(), req.industry.strip(), cid),
    )
    log_activity(user["id"], "UPDATE_COMPANY", "companies", cid, f"Cập nhật doanh nghiệp {req.name}")
    return {"ok": True, "message": "Đã lưu thông tin doanh nghiệp!"}


@router.put("/api/settings/rbac/{target_user_id}")
def api_settings_rbac(target_user_id: int, req: RoleUpdateReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    company_id = user.get("company_id") or 1
    ok = update_user_role(target_user_id, req.role, company_id=company_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ hoặc người dùng không thuộc doanh nghiệp của bạn.")
    return {"ok": True, "message": f"Đã cập nhật vai trò thành {req.role}!"}


@router.put("/api/settings/ai")
def api_settings_ai(req: AiSettingsReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    company_id = user.get("company_id") or 1
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'AI_PROVIDER_MODE';", (req.mode, company_id))
    if req.api_key:
        execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'LLM_API_KEY';", (req.api_key, company_id))
    log_activity(user["id"], "UPDATE_AI_CONFIG", "system_settings", company_id, f"Đổi chế độ AI: {req.mode}")
    return {"ok": True, "message": "Đã cập nhật cấu hình AI!"}


@router.post("/api/settings/live-code")
def api_settings_live_code(req: LiveCodeReq, user: Dict[str, Any] = Depends(require_roles("Admin", "Manager"))):
    snap = config.save_live_config(
        req.fuel_price, req.carbon_tax, req.max_load_kg, req.restricted_start, req.restricted_end
    )
    company_id = user.get("company_id") or 1
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'FUEL_PRICE_PER_LITER';", (str(req.fuel_price), company_id))
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'CARBON_TAX_RATE';", (str(req.carbon_tax), company_id))
    log_activity(user["id"], "LIVE_CODE_UPDATE", "config.py", None, f"Fuel={req.fuel_price}, CarbonTax={req.carbon_tax}, Window={req.restricted_start}-{req.restricted_end}")
    return {
        "ok": True,
        "message": "Đã ghi trực tiếp tham số mới vào config.py & tính lại toàn bộ hệ thống!",
        "config": snap,
        "sensitivity": get_sensitivity_analysis(),
    }

