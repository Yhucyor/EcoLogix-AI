"""
EcoLogix AI - Authentication, Session Tokens, RBAC & Onboarding Service
Xử lý đăng nhập (kèm access token), đăng ký, gửi lại/xác thực OTP, quên/đặt lại mật khẩu, phân quyền & Onboarding 3 bước.
"""
import secrets
from typing import Dict, Any, Optional, Tuple
from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from backend.utils.helpers import (
    create_access_token,
    hash_password,
    verify_password,
    log_activity,
    create_notification,
)
from backend.utils.validators import (
    validate_email,
    validate_password,
    validate_non_empty,
    validate_phone,
    validate_tax_code,
)
from backend import config
from backend.services.email_service import send_password_reset_email, send_verification_otp_email

VALID_ROLES = ("Admin", "Manager", "Dispatcher", "Auditor")


def get_role_permissions(role_name: str) -> list:
    rows = execute_query("SELECT permissions FROM roles WHERE name = ?;", (role_name,))
    if not rows:
        return ["READ"]
    perms = rows[0]["permissions"]
    if perms == "ALL":
        return ["ALL", "READ", "WRITE", "OPTIMIZE", "EXPORT", "SETTINGS", "FINANCIAL", "USERS"]
    return [p.strip() for p in perms.split(",") if p.strip()]


def _format_user_safe(user: Dict[str, Any]) -> Dict[str, Any]:
    has_company = bool(user.get("has_company") if user.get("has_company") is not None else 1)
    return {
        "id": user["id"],
        "company_id": user.get("company_id") or 1,
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "avatar_url": user.get("avatar_url"),
        "phone": user.get("phone"),
        "company_name": (user.get("company_name") or "EcoLogix Logistics") if has_company else "",
        "has_company": has_company,
        "is_verified": user.get("is_verified", 1),
        "permissions": get_role_permissions(user["role"]),
    }


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    rows = execute_query(
        """
        SELECT u.*, c.name as company_name
        FROM users u
        LEFT JOIN companies c ON u.company_id = c.id
        WHERE u.id = ?;
        """,
        (user_id,),
    )
    if not rows:
        return None
    return _format_user_safe(dict(rows[0]))


def authenticate_user(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    rows = execute_query(
        """
        SELECT u.*, c.name as company_name
        FROM users u
        LEFT JOIN companies c ON u.company_id = c.id
        WHERE LOWER(u.email) = LOWER(?);
        """,
        ((email or "").strip(),),
    )
    if not rows:
        return False, None, "Không tìm thấy tài khoản với email này."

    user = dict(rows[0])
    if not verify_password(password, user["password_hash"]):
        return False, None, "Mật khẩu không chính xác."

    if user.get("is_verified", 1) == 0:
        return False, None, "Tài khoản chưa được xác thực OTP. Vui lòng kích hoạt tài khoản trước khi đăng nhập."

    user_safe = _format_user_safe(user)
    token = create_access_token({
        "sub": str(user_safe["id"]),
        "email": user_safe["email"],
        "role": user_safe["role"],
        "company_id": user_safe["company_id"],
    })
    log_activity(user["id"], "USER_LOGIN", "users", user["id"], f"Đăng nhập thành công ({user['role']})")
    return True, {"user": user_safe, "access_token": token}, "Đăng nhập thành công!"


def register_user(
    name: str,
    email: str,
    password: str,
    phone: str = "",
    role: str = "Manager",
    company_name: str = "",
) -> Tuple[bool, str, Optional[str], bool]:
    ok, msg = validate_non_empty(name, "Họ tên")
    if not ok:
        return False, msg, None, False
    ok, msg = validate_email(email)
    if not ok:
        return False, msg, None, False
    ok, msg = validate_password(password)
    if not ok:
        return False, msg, None, False
    if phone and phone.strip():
        ok_p, msg_p = validate_phone(phone)
        if not ok_p:
            return False, msg_p, None, False

    normalized_role = role if role in ("Manager", "Dispatcher", "Auditor") else "Manager"
    clean_email = email.strip().lower()

    existing = execute_query("SELECT id FROM users WHERE LOWER(email) = LOWER(?);", (clean_email,))
    if existing:
        return False, "Email này đã được đăng ký trong hệ thống.", None, False

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    pw_hash = hash_password(password)
    has_comp = 1 if (company_name and company_name.strip()) else 0
    c_name = company_name.strip() if has_comp else f"Doanh nghiệp của {name.strip()}"

    from backend.database.seed import seed_starter_company_data
    comp_id = execute_insert(
        """
        INSERT INTO companies (name, tax_code, industry, size, address, city, phone, email)
        VALUES (?, ?, 'Phân phối hàng tiêu dùng (FMCG)', 'SMEs (10 - 50 nhân viên)', 'TP. Hồ Chí Minh', 'TP. Hồ Chí Minh', ?, ?);
        """,
        (c_name, f"03{secrets.randbelow(90000000) + 10000000}", phone.strip(), clean_email),
    )

    u_id = execute_insert(
        """
        INSERT INTO users (company_id, name, email, password_hash, role, phone, is_verified, has_company, reset_token)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?);
        """,
        (comp_id, name.strip(), clean_email, pw_hash, normalized_role, phone.strip(), has_comp, otp_code),
    )

    # Khởi tạo dữ liệu mẫu độc lập cho doanh nghiệp mới
    seed_starter_company_data(comp_id, c_name, admin_user_id=u_id)

    log_activity(u_id, "USER_REGISTER", "users", u_id, f"Đăng ký tài khoản mới {clean_email} ({normalized_role}) cho {c_name} (ID: {comp_id})")

    email_res = send_verification_otp_email(clean_email, name.strip(), otp_code, is_resend=False)
    if email_res.get("email_sent"):
        return True, f"Đăng ký thành công! Mã OTP 6 số đã được gửi tới email {clean_email}.", None, True
    return True, f"Đăng ký thành công! Mã xác thực OTP (Demo): {otp_code}", otp_code, False


def resend_verification_otp(email: str) -> Tuple[bool, str, Optional[str], bool]:
    clean_email = (email or "").strip().lower()
    rows = execute_query("SELECT id, name, email, is_verified FROM users WHERE LOWER(email) = LOWER(?);", (clean_email,))
    if not rows:
        return False, "Không tìm thấy tài khoản với email này.", None, False
    user = dict(rows[0])
    if user["is_verified"] == 1:
        return False, "Tài khoản này đã được xác thực trước đó.", None, False
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    execute_update("UPDATE users SET reset_token = ? WHERE id = ?;", (otp_code, user["id"]))
    log_activity(user["id"], "RESEND_OTP", "users", user["id"], f"Gửi lại OTP xác thực tới {user['email']}")

    email_res = send_verification_otp_email(user["email"], user.get("name", ""), otp_code, is_resend=True)
    if email_res.get("email_sent"):
        return True, f"Đã gửi lại mã OTP mới tới email {user['email']}.", None, True
    return True, f"Đã gửi lại mã OTP mới (Demo): {otp_code}", otp_code, False


def verify_user_account(email: str, otp_code: str) -> Tuple[bool, str]:
    rows = execute_query("SELECT id, reset_token, is_verified FROM users WHERE LOWER(email) = LOWER(?);", ((email or "").strip(),))
    if not rows:
        return False, "Email không tồn tại."
    user = dict(rows[0])
    if user["is_verified"] == 1:
        return True, "Tài khoản đã được xác thực trước đó."
    if str(user.get("reset_token") or "").strip() != str(otp_code).strip():
        return False, "Mã xác thực OTP không khớp."
    execute_update("UPDATE users SET is_verified = 1, reset_token = NULL WHERE id = ?;", (user["id"],))
    log_activity(user["id"], "USER_VERIFY", "users", user["id"], "Xác thực tài khoản thành công")
    return True, "Xác thực tài khoản thành công! Bạn có thể đăng nhập ngay."


def request_password_reset(email: str) -> Tuple[bool, str, Optional[str], bool]:
    clean_email = (email or "").strip().lower()
    rows = execute_query("SELECT id, name, email FROM users WHERE LOWER(email) = LOWER(?);", (clean_email,))
    if not rows:
        return False, "Email không tồn tại trong hệ thống.", None, False
    user = dict(rows[0])
    token = f"RST-{secrets.randbelow(900000) + 100000}"
    execute_update("UPDATE users SET reset_token = ? WHERE id = ?;", (token, user["id"]))
    log_activity(user["id"], "REQUEST_PASSWORD_RESET", "users", user["id"], f"Yêu cầu khôi phục mật khẩu ({user['email']})")

    email_res = send_password_reset_email(user["email"], user.get("name", ""), token)
    if email_res.get("email_sent"):
        return True, f"Mã khôi phục mật khẩu đã được gửi tới email {user['email']}.", None, True
    return True, f"Mã khôi phục mật khẩu (Demo): {token}", token, False


def reset_password(email: str, token: str, new_password: str) -> Tuple[bool, str]:
    ok, msg = validate_password(new_password)
    if not ok:
        return False, msg
    rows = execute_query("SELECT id, reset_token FROM users WHERE LOWER(email) = LOWER(?);", ((email or "").strip(),))
    if not rows:
        return False, "Email không tồn tại."
    if not rows[0]["reset_token"] or rows[0]["reset_token"] != (token or "").strip():
        return False, "Mã khôi phục không hợp lệ hoặc đã hết hạn."
    execute_update(
        "UPDATE users SET password_hash = ?, reset_token = NULL, is_verified = 1 WHERE id = ?;",
        (hash_password(new_password), rows[0]["id"]),
    )
    log_activity(rows[0]["id"], "PASSWORD_RESET", "users", rows[0]["id"], "Đặt lại mật khẩu thành công")
    return True, "Đặt lại mật khẩu thành công! Vui lòng đăng nhập lại."


def get_all_users(company_id: Optional[int] = None) -> list:
    if company_id:
        return rows_to_dicts(execute_query(
            "SELECT id, company_id, name, email, role, phone, is_verified, created_at FROM users WHERE company_id = ? ORDER BY id ASC;",
            (company_id,),
        ))
    return rows_to_dicts(execute_query(
        "SELECT id, company_id, name, email, role, phone, is_verified, created_at FROM users ORDER BY id ASC;"
    ))


def get_all_roles() -> list:
    return rows_to_dicts(execute_query("SELECT * FROM roles ORDER BY id ASC;"))


def update_user_role(user_id: int, new_role: str, company_id: Optional[int] = None) -> bool:
    if new_role not in VALID_ROLES:
        return False
    if company_id:
        updated = execute_update("UPDATE users SET role = ? WHERE id = ? AND company_id = ?;", (new_role, user_id, company_id))
    else:
        updated = execute_update("UPDATE users SET role = ? WHERE id = ?;", (new_role, user_id))
    log_activity(user_id, "UPDATE_ROLE", "users", user_id, f"Đổi vai trò thành {new_role}")
    return updated > 0


def update_user_profile(user_id: int, name: str, phone: str) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Họ tên")
    if not ok:
        return False, msg
    execute_update("UPDATE users SET name = ?, phone = ? WHERE id = ?;", (name.strip(), phone.strip(), user_id))
    log_activity(user_id, "UPDATE_PROFILE", "users", user_id, f"Cập nhật hồ sơ cá nhân: {name}")
    return True, "Đã cập nhật hồ sơ cá nhân."


def complete_onboarding(payload: Dict[str, Any], user_id: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
    comp_name = payload.get("company_name", "").strip()
    tax_code = payload.get("tax_code", "").strip()
    ok, msg = validate_non_empty(comp_name, "Tên doanh nghiệp")
    if not ok:
        return False, msg, {}
    if tax_code:
        ok_tax, msg_tax = validate_tax_code(tax_code)
        if not ok_tax:
            return False, msg_tax, {}

    user_rows = execute_query("SELECT id, company_id FROM users WHERE id = ?;", (user_id,))
    if not user_rows:
        return False, "Không tìm thấy người dùng.", {}
    user_rec = dict(user_rows[0])
    company_id = user_rec.get("company_id")

    # Đảm bảo mã số thuế không bị trùng lặp giữa các doanh nghiệp
    clean_tax = tax_code.strip() if tax_code else f"03{secrets.randbelow(90000000)+10000000}"
    if company_id:
        dup = execute_query("SELECT id FROM companies WHERE tax_code = ? AND id != ?;", (clean_tax, company_id))
        if dup:
            clean_tax = f"{clean_tax}-{secrets.randbelow(900)+100}"

    if not company_id:
        company_id = execute_insert(
            """
            INSERT INTO companies (name, tax_code, address, industry, size, city)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                comp_name,
                clean_tax,
                payload.get("address", "TP. Thủ Đức, TP.HCM"),
                payload.get("industry", "Phân phối hàng tiêu dùng (FMCG)"),
                payload.get("size", "SMEs (10 - 50 nhân viên)"),
                payload.get("city", "TP. Hồ Chí Minh"),
            ),
        )
        execute_update("UPDATE users SET company_id = ?, has_company = 1 WHERE id = ?;", (company_id, user_id))
    else:
        execute_update(
            """
            UPDATE companies
            SET name = ?, tax_code = ?, address = ?, industry = ?, size = ?, city = ?
            WHERE id = ?;
            """,
            (
                comp_name,
                clean_tax,
                payload.get("address", "TP. Thủ Đức, TP.HCM"),
                payload.get("industry", "Phân phối hàng tiêu dùng (FMCG)"),
                payload.get("size", "SMEs (10 - 50 nhân viên)"),
                payload.get("city", "TP. Hồ Chí Minh"),
                company_id,
            ),
        )

    wh_name = (payload.get("warehouse_name") or "").strip()
    if wh_name:
        wh_code = (payload.get("warehouse_code") or f"WH-C{company_id}-{secrets.randbelow(900)+100}").strip()
        existing_wh = execute_query("SELECT id FROM warehouses WHERE company_id = ? AND code = ?;", (company_id, wh_code))
        if not existing_wh:
            execute_insert(
                """
                INSERT INTO warehouses (company_id, name, code, address, lat, lng, capacity_m3, current_utilization_pct, is_central_hub)
                VALUES (?, ?, ?, ?, 10.845, 106.765, ?, 45.0, 0);
                """,
                (company_id, wh_name, wh_code, payload.get("warehouse_address", "TP. Thủ Đức, TP.HCM"), float(payload.get("warehouse_capacity", 2500))),
            )

    plate = (payload.get("vehicle_plate") or "").strip()
    veh_name = (payload.get("vehicle_name") or "").strip()
    if plate and veh_name:
        existing_v = execute_query("SELECT id FROM vehicles WHERE company_id = ? AND plate_number = ?;", (company_id, plate))
        if not existing_v:
            execute_insert(
                """
                INSERT INTO vehicles (company_id, plate_number, vehicle_name, vehicle_type, max_load_kg, fuel_type, fuel_consumption_per_100km, operational_cost_per_km, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Available');
                """,
                (
                    company_id,
                    plate,
                    veh_name,
                    payload.get("vehicle_type", "Tải nhẹ đô thị"),
                    float(payload.get("max_load_kg", 1500)),
                    payload.get("fuel_type", "Diesel"),
                    float(payload.get("fuel_consumption", 11.5)),
                    float(payload.get("cost_per_km", 3800)),
                ),
            )

    fuel_price = int(payload.get("fuel_price", config.FUEL_PRICE_PER_LITER))
    max_load = int(payload.get("max_load_kg", config.MAX_VEHICLE_LOAD_KG))
    carbon_tax = int(payload.get("carbon_tax", config.CARBON_TAX_RATE))
    tw = list(config.RESTRICTED_TIME_WINDOW)
    config.save_live_config(fuel_price, carbon_tax, max_load, tw[0], tw[1])

    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'FUEL_PRICE_PER_LITER';", (str(fuel_price), company_id))
    execute_update("UPDATE system_settings SET setting_value = ? WHERE company_id = ? AND setting_key = 'MAX_VEHICLE_LOAD_KG';", (str(max_load), company_id))
    if user_id:
        execute_update("UPDATE users SET has_company = 1 WHERE id = ?;", (user_id,))

    log_activity(user_id, "COMPLETE_ONBOARDING", "companies", company_id, f"Thiết lập doanh nghiệp {comp_name} hoàn tất")
    create_notification(user_id, "Chào mừng đến với EcoLogix AI", f"Hồ sơ vận hành của {comp_name} đã sẵn sàng.", "success")

    return True, "Thiết lập doanh nghiệp và dữ liệu vận hành hoàn tất!", {
        "company_name": comp_name,
        "fuel_price": fuel_price,
        "max_load_kg": max_load,
        "user": get_user_by_id(user_id) if user_id else None,
    }


def get_onboarding_context(user_id: int) -> Dict[str, Any]:
    """Trả về trạng thái doanh nghiệp hiện có và thông số mặc định cho modal tiếp tục/chỉnh sửa."""
    user = get_user_by_id(user_id)
    company_id = (user.get("company_id") if user else None) or 1
    has_company = bool(user and user.get("has_company"))
    comp_rows = rows_to_dicts(execute_query("SELECT id, name, tax_code, industry, size, address, city, phone, email FROM companies WHERE id = ?;", (company_id,)))
    wh_rows = rows_to_dicts(execute_query("SELECT name, code, address FROM warehouses WHERE company_id = ? ORDER BY id DESC LIMIT 1;", (company_id,)))
    veh_rows = rows_to_dicts(execute_query("SELECT vehicle_name, plate_number, max_load_kg, operational_cost_per_km FROM vehicles WHERE company_id = ? ORDER BY id DESC LIMIT 1;", (company_id,)))
    return {
        "has_company": has_company,
        "company": comp_rows[0] if (has_company and comp_rows) else None,
        "warehouse": wh_rows[0] if (has_company and wh_rows) else None,
        "vehicle": veh_rows[0] if (has_company and veh_rows) else None,
        "config": {
            "fuel_price": config.FUEL_PRICE_PER_LITER,
            "max_load_kg": config.MAX_VEHICLE_LOAD_KG,
            "cost_per_km": config.DRIVER_AND_DEPRECIATION_PER_KM,
        },
    }
