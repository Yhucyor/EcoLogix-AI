"""
EcoLogix AI - Order Management Service
Quản lý đơn hàng, chi tiết sản phẩm (order_items), trừ tồn kho, lọc & phân trang (Full CRUD).
"""
from typing import List, Dict, Any, Optional, Tuple
from database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from utils.helpers import log_activity, create_notification
from utils.validators import validate_non_empty


def get_orders(status: Optional[str] = None, province: Optional[str] = None, search: str = "", limit: int = 100, offset: int = 0) -> list:
    query = """
    SELECT o.*, c.name as customer_name, c.district, c.province, c.address as delivery_address,
           w.name as warehouse_name
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    JOIN warehouses w ON o.warehouse_id = w.id
    WHERE 1=1
    """
    params = []
    if status and status != "ALL":
        query += " AND o.status = ?"
        params.append(status)
    if province and province != "ALL":
        query += " AND c.province = ?"
        params.append(province)
    if search and search.strip():
        kw = f"%{search.strip()}%"
        query += " AND (o.order_code LIKE ? OR c.name LIKE ? OR c.district LIKE ?)"
        params.extend([kw, kw, kw])
    query += " ORDER BY o.id DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])
    return rows_to_dicts(execute_query(query, tuple(params)))


def get_order_stats() -> dict:
    rows = execute_query("""
    SELECT status, COUNT(*) as cnt, COALESCE(SUM(total_amount), 0) as total_val
    FROM orders GROUP BY status;
    """)
    counts = {r["status"]: r["cnt"] for r in rows}
    total_val = sum(r["total_val"] for r in rows)
    return {
        "total": sum(counts.values()),
        "pending": counts.get("PENDING", 0),
        "processing": counts.get("PROCESSING", 0),
        "shipping": counts.get("SHIPPING", 0),
        "completed": counts.get("COMPLETED", 0),
        "cancelled": counts.get("CANCELLED", 0),
        "total_revenue_vnd": round(total_val, 0),
    }


def get_order_detail(order_id: int) -> Optional[dict]:
    rows = execute_query("""
    SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.address as delivery_address,
           c.district, c.province, w.name as warehouse_name, w.address as pickup_address
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    JOIN warehouses w ON o.warehouse_id = w.id
    WHERE o.id = ?;
    """, (order_id,))
    if not rows:
        return None
    order = dict(rows[0])
    items = rows_to_dicts(execute_query("""
    SELECT oi.*, p.sku, p.name as product_name, p.unit, p.weight_kg
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.order_id = ?;
    """, (order_id,)))
    order["items"] = items
    return order


def create_order(
    order_code: str,
    customer_id: int,
    warehouse_id: int,
    time_window_start: str,
    time_window_end: str,
    items: List[Dict[str, Any]],
    shipping_fee: float = 180000.0,
    manual_weight_kg: Optional[float] = None,
    manual_amount: Optional[float] = None,
    user_id: int = 1,
) -> Tuple[bool, str, Optional[int]]:
    ok, msg = validate_non_empty(order_code, "Mã đơn hàng")
    if not ok:
        return False, msg, None

    if execute_query("SELECT id FROM orders WHERE LOWER(order_code) = LOWER(?);", (order_code.strip(),)):
        return False, f"Mã đơn hàng `{order_code}` đã tồn tại.", None

    cust_rows = execute_query("SELECT district FROM customers WHERE id = ?;", (customer_id,))
    if not cust_rows:
        return False, "Khách hàng không hợp lệ.", None
    is_restricted = 1 if cust_rows[0]["district"] in ("Quận 1", "Quận 3", "Quận 5", "Quận 10") else 0

    total_weight = 0.0
    total_amount = 0.0
    resolved_items = []
    if items:
        for item in items:
            p_rows = execute_query("SELECT id, unit_price, weight_kg FROM products WHERE id = ?;", (item["product_id"],))
            if not p_rows:
                continue
            qty = max(1, int(item.get("quantity", 1)))
            p = p_rows[0]
            total_weight += p["weight_kg"] * qty
            total_amount += p["unit_price"] * qty
            resolved_items.append((p["id"], qty, p["unit_price"]))
    else:
        total_weight = float(manual_weight_kg or 100.0)
        total_amount = float(manual_amount or 3500000.0)

    order_id = execute_insert(
        """
        INSERT INTO orders (company_id, order_code, customer_id, warehouse_id, status, total_weight_kg, total_amount, shipping_fee, time_window_start, time_window_end, is_urban_restricted)
        VALUES (1, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?);
        """,
        (order_code.strip().upper(), customer_id, warehouse_id, round(total_weight, 1), round(total_amount, 0), float(shipping_fee), time_window_start, time_window_end, is_restricted),
    )

    for p_id, qty, u_price in resolved_items:
        execute_insert(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);",
            (order_id, p_id, qty, u_price),
        )
        execute_update(
            "UPDATE inventory SET quantity = MAX(0, quantity - ?), last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;",
            (qty, p_id, warehouse_id),
        )

    log_activity(user_id, "CREATE_ORDER", "orders", order_id, f"Tạo đơn hàng {order_code} ({round(total_weight, 1)} kg)")
    create_notification(user_id, f"Đơn hàng mới {order_code.upper()}", f"Đơn trọng lượng {round(total_weight, 1)} kg đã sẵn sàng vào hàng đợi tối ưu lộ trình.", "info")
    return True, f"Đã tạo đơn hàng `{order_code.upper()}` thành công!", order_id


def update_order_status(order_id_or_code, new_status: str, user_id: int = 1) -> Tuple[bool, str]:
    valid_statuses = {"PENDING", "PROCESSING", "SHIPPING", "COMPLETED", "CANCELLED"}
    if new_status not in valid_statuses:
        return False, "Trạng thái không hợp lệ."
    if isinstance(order_id_or_code, int) or str(order_id_or_code).isdigit():
        cnt = execute_update("UPDATE orders SET status = ? WHERE id = ?;", (new_status, int(order_id_or_code)))
    else:
        cnt = execute_update("UPDATE orders SET status = ? WHERE order_code = ?;", (new_status, str(order_id_or_code)))
    if cnt == 0:
        return False, "Không tìm thấy đơn hàng."
    log_activity(user_id, "UPDATE_ORDER_STATUS", "orders", None, f"Đơn {order_id_or_code} -> {new_status}")
    return True, f"Đã cập nhật đơn `{order_id_or_code}` sang `{new_status}`!"


def delete_order(order_id: int, user_id: int = 1) -> Tuple[bool, str]:
    in_route = execute_query("SELECT COUNT(*) as cnt FROM route_stops WHERE order_id = ?;", (order_id,))
    if in_route and in_route[0]["cnt"] > 0:
        execute_update("DELETE FROM route_stops WHERE order_id = ?;", (order_id,))
    execute_update("DELETE FROM order_items WHERE order_id = ?;", (order_id,))
    cnt = execute_update("DELETE FROM orders WHERE id = ?;", (order_id,))
    if cnt == 0:
        return False, "Không tìm thấy đơn hàng."
    log_activity(user_id, "DELETE_ORDER", "orders", order_id, f"Xóa đơn hàng #{order_id}")
    return True, "Đã xóa đơn hàng."

