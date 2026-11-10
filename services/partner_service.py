"""
EcoLogix AI - Customer & Supplier Partner Management Service
Quản lý đối tác phân phối, lịch sử đơn hàng khách hàng và công nợ nhà cung cấp (Full CRUD).
"""
from typing import Tuple
from database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from utils.helpers import log_activity
from utils.validators import validate_non_empty

DISTRICT_COORDS = {
    "Quận 1": (10.7769, 106.7009),
    "Quận 3": (10.7828, 106.6872),
    "Quận 5": (10.7554, 106.6669),
    "Quận 10": (10.7725, 106.6672),
    "TP. Thủ Đức": (10.8495, 106.7718),
    "Dĩ An": (10.9022, 106.7584),
    "Thuận An": (10.9333, 106.7167),
    "Thủ Dầu Một": (10.9804, 106.6746),
    "Biên Hòa": (10.9574, 106.8427),
    "Long Thành": (10.7932, 106.9538),
}


def get_customers(search: str = "", tier: str = "ALL") -> list:
    query = """
    SELECT c.*,
           COALESCE(COUNT(o.id), 0) as order_count,
           COALESCE(SUM(o.total_amount), c.total_spent) as lifetime_value
    FROM customers c
    LEFT JOIN orders o ON c.id = o.customer_id
    WHERE 1=1
    """
    params = []
    if tier and tier != "ALL":
        query += " AND c.customer_tier = ?"
        params.append(tier)
    if search and search.strip():
        kw = f"%{search.strip()}%"
        query += " AND (c.name LIKE ? OR c.district LIKE ? OR c.province LIKE ? OR c.phone LIKE ?)"
        params.extend([kw, kw, kw, kw])
    query += " GROUP BY c.id ORDER BY lifetime_value DESC;"
    return rows_to_dicts(execute_query(query, tuple(params)))


def get_customer_orders(customer_id: int) -> list:
    return rows_to_dicts(execute_query(
        "SELECT id, order_code, status, total_weight_kg, total_amount, created_at FROM orders WHERE customer_id = ? ORDER BY id DESC;",
        (customer_id,),
    ))


def add_customer(name: str, phone: str, email: str, address: str, district: str, province: str, tier: str = "Standard", user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Tên khách hàng")
    if not ok:
        return False, msg
    lat, lng = DISTRICT_COORDS.get(district, (10.8000, 106.7200))
    c_id = execute_insert(
        """
        INSERT INTO customers (company_id, name, phone, email, address, district, province, lat, lng, customer_tier, total_spent)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
        """,
        (name.strip(), phone.strip(), email.strip(), address.strip(), district, province, lat, lng, tier),
    )
    log_activity(user_id, "CREATE_CUSTOMER", "customers", c_id, f"Thêm khách hàng {name}")
    return True, f"Đã thêm khách hàng `{name}` thành công!"


def update_customer(customer_id: int, name: str, phone: str, email: str, address: str, district: str, province: str, tier: str, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Tên khách hàng")
    if not ok:
        return False, msg
    lat, lng = DISTRICT_COORDS.get(district, (10.8000, 106.7200))
    execute_update(
        """
        UPDATE customers SET name = ?, phone = ?, email = ?, address = ?, district = ?, province = ?, lat = ?, lng = ?, customer_tier = ?
        WHERE id = ?;
        """,
        (name.strip(), phone.strip(), email.strip(), address.strip(), district, province, lat, lng, tier, customer_id),
    )
    log_activity(user_id, "UPDATE_CUSTOMER", "customers", customer_id, f"Cập nhật khách hàng #{customer_id}")
    return True, "Đã cập nhật thông tin khách hàng."


def delete_customer(customer_id: int, user_id: int = 1) -> Tuple[bool, str]:
    used = execute_query("SELECT COUNT(*) as cnt FROM orders WHERE customer_id = ?;", (customer_id,))
    if used and used[0]["cnt"] > 0:
        return False, "Không thể xóa khách hàng đã có lịch sử đơn hàng."
    execute_update("DELETE FROM customers WHERE id = ?;", (customer_id,))
    log_activity(user_id, "DELETE_CUSTOMER", "customers", customer_id, f"Xóa khách hàng #{customer_id}")
    return True, "Đã xóa khách hàng."


def get_suppliers(search: str = "") -> list:
    query = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if search and search.strip():
        kw = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR products_supplied LIKE ? OR address LIKE ?)"
        params.extend([kw, kw, kw])
    query += " ORDER BY id ASC;"
    return rows_to_dicts(execute_query(query, tuple(params)))


def add_supplier(name: str, phone: str, email: str, address: str, products_supplied: str, debt_vnd: float = 0.0, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Tên nhà cung cấp")
    if not ok:
        return False, msg
    s_id = execute_insert(
        """
        INSERT INTO suppliers (company_id, name, phone, email, address, products_supplied, debt_vnd)
        VALUES (1, ?, ?, ?, ?, ?, ?);
        """,
        (name.strip(), phone.strip(), email.strip(), address.strip(), products_supplied.strip(), float(debt_vnd)),
    )
    log_activity(user_id, "CREATE_SUPPLIER", "suppliers", s_id, f"Thêm nhà cung cấp {name}")
    return True, f"Đã thêm nhà cung cấp `{name}` thành công!"


def update_supplier_debt(supplier_id: int, new_debt_vnd: float, user_id: int = 1) -> Tuple[bool, str]:
    execute_update("UPDATE suppliers SET debt_vnd = ? WHERE id = ?;", (max(0.0, float(new_debt_vnd)), supplier_id))
    log_activity(user_id, "UPDATE_SUPPLIER_DEBT", "suppliers", supplier_id, f"Cập nhật công nợ NCC #{supplier_id}: {new_debt_vnd:,.0f} đ")
    return True, "Đã cập nhật công nợ nhà cung cấp."


def delete_supplier(supplier_id: int, user_id: int = 1) -> Tuple[bool, str]:
    execute_update("DELETE FROM suppliers WHERE id = ?;", (supplier_id,))
    log_activity(user_id, "DELETE_SUPPLIER", "suppliers", supplier_id, f"Xóa nhà cung cấp #{supplier_id}")
    return True, "Đã xóa nhà cung cấp."

