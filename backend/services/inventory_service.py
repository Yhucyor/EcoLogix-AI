"""
EcoLogix AI - Inventory, Warehouse & SKU Service
Quản lý kho hàng, SKU sản phẩm, kiểm kê, điều chuyển giữa các kho và lịch sử giao dịch (Full CRUD).
"""
from typing import Tuple, Optional
from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from backend.utils.helpers import log_activity, create_notification
from backend.utils.validators import validate_non_empty, validate_positive


def get_all_warehouses() -> list:
    return rows_to_dicts(execute_query("SELECT * FROM warehouses ORDER BY is_central_hub DESC, id ASC;"))


def add_warehouse(name: str, code: str, address: str, capacity_m3: float, lat: float = 10.85, lng: float = 106.77, user_id: int = 1) -> Tuple[bool, str]:
    for val, label in [(name, "Tên kho"), (code, "Mã kho"), (address, "Địa chỉ")]:
        ok, msg = validate_non_empty(val, label)
        if not ok:
            return False, msg
    if execute_query("SELECT id FROM warehouses WHERE LOWER(code) = LOWER(?);", (code.strip(),)):
        return False, f"Mã kho `{code}` đã tồn tại."
    w_id = execute_insert(
        """
        INSERT INTO warehouses (company_id, name, code, address, lat, lng, capacity_m3, current_utilization_pct, is_central_hub)
        VALUES (1, ?, ?, ?, ?, ?, ?, 0.0, 0);
        """,
        (name.strip(), code.strip().upper(), address.strip(), float(lat), float(lng), float(capacity_m3)),
    )
    # Khởi tạo tồn kho 0 cho các sản phẩm hiện có
    prods = execute_query("SELECT id, min_stock FROM products;")
    for p in prods:
        execute_insert(
            "INSERT OR IGNORE INTO inventory (warehouse_id, product_id, quantity, safety_stock, reorder_point) VALUES (?, ?, 0, ?, ?);",
            (w_id, p["id"], int((p["min_stock"] or 40) * 0.5), int((p["min_stock"] or 40) * 1.2)),
        )
    log_activity(user_id, "CREATE_WAREHOUSE", "warehouses", w_id, f"Thêm kho {name} ({code})")
    return True, f"Đã thêm kho `{name}` thành công!"


def update_warehouse(warehouse_id: int, name: str, address: str, capacity_m3: float, utilization_pct: float, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Tên kho")
    if not ok:
        return False, msg
    execute_update(
        "UPDATE warehouses SET name = ?, address = ?, capacity_m3 = ?, current_utilization_pct = ? WHERE id = ?;",
        (name.strip(), address.strip(), float(capacity_m3), float(utilization_pct), warehouse_id),
    )
    log_activity(user_id, "UPDATE_WAREHOUSE", "warehouses", warehouse_id, f"Cập nhật thông tin kho {name}")
    return True, "Đã cập nhật thông tin kho hàng."


def get_all_products() -> list:
    return rows_to_dicts(execute_query("""
    SELECT p.*, COALESCE(SUM(i.quantity), 0) as total_stock,
           COALESCE(SUM(i.safety_stock), 0) as total_safety
    FROM products p
    LEFT JOIN inventory i ON p.id = i.product_id
    GROUP BY p.id
    ORDER BY p.id ASC;
    """))


def get_inventory_status(warehouse_id: Optional[int] = None, search: str = "") -> list:
    query = """
    SELECT i.*, p.sku, p.name as product_name, p.category, p.unit, p.unit_price, p.weight_kg,
           w.name as warehouse_name, w.code as warehouse_code
    FROM inventory i
    JOIN products p ON i.product_id = p.id
    JOIN warehouses w ON i.warehouse_id = w.id
    WHERE 1=1
    """
    params = []
    if warehouse_id:
        query += " AND i.warehouse_id = ?"
        params.append(warehouse_id)
    if search and search.strip():
        kw = f"%{search.strip()}%"
        query += " AND (p.sku LIKE ? OR p.name LIKE ? OR w.name LIKE ?)"
        params.extend([kw, kw, kw])
    query += " ORDER BY (i.quantity - i.safety_stock) ASC;"
    return rows_to_dicts(execute_query(query, tuple(params)))


def add_product(company_id: int, sku: str, name: str, category: str, unit: str, unit_price: float, weight_kg: float, min_stock: int, max_stock: int, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(sku, "Mã SKU")
    if not ok:
        return False, msg
    ok, msg = validate_non_empty(name, "Tên sản phẩm")
    if not ok:
        return False, msg
    ok, msg = validate_positive(unit_price, "Đơn giá")
    if not ok:
        return False, msg

    if execute_query("SELECT id FROM products WHERE LOWER(sku) = LOWER(?);", (sku.strip(),)):
        return False, f"Mã SKU `{sku}` đã tồn tại trong danh mục."

    p_id = execute_insert(
        """
        INSERT INTO products (company_id, sku, name, category, unit, unit_price, weight_kg, min_stock, max_stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (company_id, sku.strip().upper(), name.strip(), category, unit, float(unit_price), float(weight_kg), int(min_stock), int(max_stock)),
    )

    whs = get_all_warehouses()
    for w in whs:
        execute_insert(
            """
            INSERT INTO inventory (warehouse_id, product_id, quantity, safety_stock, reorder_point)
            VALUES (?, ?, ?, ?, ?);
            """,
            (w["id"], p_id, int(min_stock), max(10, int(min_stock * 0.5)), max(20, int(min_stock * 1.2))),
        )
    log_activity(user_id, "CREATE_PRODUCT", "products", p_id, f"Thêm SKU mới {sku} - {name}")
    return True, f"Đã thêm sản phẩm `{sku.upper()} - {name}` thành công!"


def update_product(product_id: int, name: str, category: str, unit: str, unit_price: float, weight_kg: float, min_stock: int, max_stock: int, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(name, "Tên sản phẩm")
    if not ok:
        return False, msg
    execute_update(
        """
        UPDATE products SET name = ?, category = ?, unit = ?, unit_price = ?, weight_kg = ?, min_stock = ?, max_stock = ?
        WHERE id = ?;
        """,
        (name.strip(), category, unit, float(unit_price), float(weight_kg), int(min_stock), int(max_stock), product_id),
    )
    log_activity(user_id, "UPDATE_PRODUCT", "products", product_id, f"Cập nhật sản phẩm #{product_id}: {name}")
    return True, "Đã cập nhật thông tin sản phẩm."


def delete_product(product_id: int, user_id: int = 1) -> Tuple[bool, str]:
    used = execute_query("SELECT COUNT(*) as cnt FROM order_items WHERE product_id = ?;", (product_id,))
    if used and used[0]["cnt"] > 0:
        return False, "Không thể xóa sản phẩm đã phát sinh trong đơn hàng."
    execute_update("DELETE FROM forecasts WHERE product_id = ?;", (product_id,))
    execute_update("DELETE FROM inventory_transactions WHERE product_id = ?;", (product_id,))
    execute_update("DELETE FROM inventory WHERE product_id = ?;", (product_id,))
    execute_update("DELETE FROM products WHERE id = ?;", (product_id,))
    log_activity(user_id, "DELETE_PRODUCT", "products", product_id, f"Xóa sản phẩm #{product_id}")
    return True, "Đã xóa sản phẩm khỏi danh mục."


def _check_and_alert_low_stock(product_id: int, warehouse_id: int, user_id: int = 1):
    rows = execute_query(
        """
        SELECT i.quantity, i.safety_stock, p.sku, p.name, w.name as warehouse_name
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN warehouses w ON i.warehouse_id = w.id
        WHERE i.product_id = ? AND i.warehouse_id = ?;
        """,
        (product_id, warehouse_id),
    )
    if rows:
        r = rows[0]
        if r["quantity"] <= r["safety_stock"]:
            create_notification(
                user_id,
                f"Cảnh báo tồn kho thấp {r['sku']}",
                f"{r['name']} tại {r['warehouse_name']} chỉ còn {r['quantity']} (ngưỡng an toàn {r['safety_stock']}).",
                "warning",
            )


def record_transaction(product_id: int, warehouse_id: int, trans_type: str, quantity: int, note: str = "", ref_code: str = "", user_id: int = 1) -> Tuple[bool, str]:
    qty = int(quantity)
    if trans_type != "ADJUST" and qty <= 0:
        return False, "Số lượng giao dịch phải lớn hơn 0."

    cur = execute_query("SELECT quantity FROM inventory WHERE product_id = ? AND warehouse_id = ?;", (product_id, warehouse_id))
    cur_qty = cur[0]["quantity"] if cur else 0

    if trans_type == "IN":
        execute_update("UPDATE inventory SET quantity = quantity + ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;", (qty, product_id, warehouse_id))
    elif trans_type == "OUT":
        if cur_qty < qty:
            return False, f"Tồn kho không đủ để xuất (hiện còn {cur_qty})."
        execute_update("UPDATE inventory SET quantity = quantity - ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;", (qty, product_id, warehouse_id))
    elif trans_type == "ADJUST":
        if qty < 0:
            return False, "Số lượng kiểm kê thực tế không được âm."
        execute_update("UPDATE inventory SET quantity = ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;", (qty, product_id, warehouse_id))
    else:
        return False, f"Loại giao dịch không hợp lệ: {trans_type}"

    tx_id = execute_insert(
        """
        INSERT INTO inventory_transactions (product_id, warehouse_id, transaction_type, quantity, reference_code, note)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (product_id, warehouse_id, trans_type, qty, ref_code or f"TX-{trans_type}", note),
    )
    _check_and_alert_low_stock(product_id, warehouse_id, user_id)
    log_activity(user_id, f"INVENTORY_{trans_type}", "inventory_transactions", tx_id, f"{trans_type} {qty} đơn vị (SKU #{product_id})")
    return True, f"Đã ghi nhận giao dịch {trans_type} ({qty} đơn vị) thành công!"


def transfer_stock(product_id: int, from_wh_id: int, to_wh_id: int, quantity: int, note: str = "", user_id: int = 1) -> Tuple[bool, str]:
    if from_wh_id == to_wh_id:
        return False, "Kho nguồn và kho đích không được trùng nhau."
    qty = int(quantity)
    if qty <= 0:
        return False, "Số lượng điều chuyển phải lớn hơn 0."

    cur = execute_query("SELECT quantity FROM inventory WHERE product_id = ? AND warehouse_id = ?;", (product_id, from_wh_id))
    if not cur or cur[0]["quantity"] < qty:
        avail = cur[0]["quantity"] if cur else 0
        return False, f"Kho nguồn chỉ còn {avail} đơn vị, không đủ để điều chuyển {qty}."

    execute_update("UPDATE inventory SET quantity = quantity - ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;", (qty, product_id, from_wh_id))
    execute_update("UPDATE inventory SET quantity = quantity + ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?;", (qty, product_id, to_wh_id))

    tx_id = execute_insert(
        "INSERT INTO inventory_transactions (product_id, warehouse_id, transaction_type, quantity, reference_code, note) VALUES (?, ?, 'TRANSFER', ?, ?, ?);",
        (product_id, from_wh_id, qty, f"TRF-{from_wh_id}->{to_wh_id}", note or f"Điều chuyển từ kho #{from_wh_id} sang kho #{to_wh_id}"),
    )
    _check_and_alert_low_stock(product_id, from_wh_id, user_id)
    log_activity(user_id, "INVENTORY_TRANSFER", "inventory_transactions", tx_id, f"Điều chuyển {qty} SKU #{product_id}: Kho {from_wh_id} -> {to_wh_id}")
    return True, f"Đã điều chuyển {qty} đơn vị sang kho đích thành công!"


def get_transaction_history(limit: int = 50) -> list:
    return rows_to_dicts(execute_query(
        """
        SELECT t.*, p.sku, p.name as product_name, w.name as warehouse_name
        FROM inventory_transactions t
        JOIN products p ON t.product_id = p.id
        JOIN warehouses w ON t.warehouse_id = w.id
        ORDER BY t.id DESC
        LIMIT ?;
        """,
        (limit,),
    ))


def get_inventory_metrics() -> dict:
    rows = execute_query("SELECT SUM(quantity) as total_qty, COUNT(*) as total_rows, SUM(CASE WHEN quantity <= safety_stock THEN 1 ELSE 0 END) as low_cnt FROM inventory;")
    r = rows[0] if rows else {"total_qty": 0, "total_rows": 0, "low_cnt": 0}
    total_rows = r["total_rows"] or 1
    health_pct = round(((total_rows - (r["low_cnt"] or 0)) / total_rows) * 100.0, 1)
    return {
        "total_units": int(r["total_qty"] or 0),
        "total_sku_slots": int(total_rows),
        "low_stock_alerts": int(r["low_cnt"] or 0),
        "inventory_efficiency_pct": min(99.5, max(72.0, health_pct)),
    }
