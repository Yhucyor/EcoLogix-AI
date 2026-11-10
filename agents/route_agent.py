"""Agent 4: Route Optimization Agent (CVRPTW & Fleet Comparison)."""
import importlib
import config
from database.connection import execute_query, rows_to_dicts
from services.routing_service import get_vehicles, optimize_routes_for_orders


def run_route_agent(province_filter: str = "Bình Dương") -> dict:
    importlib.reload(config)
    orders = rows_to_dicts(execute_query(
        """
        SELECT o.id, o.order_code, o.total_weight_kg, c.province, c.district
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.status IN ('PENDING', 'PROCESSING', 'SHIPPING')
          AND LOWER(c.province) LIKE LOWER(?);
        """,
        (f"%{province_filter}%",),
    ))
    if not orders:
        orders = rows_to_dicts(execute_query(
            "SELECT id, order_code, total_weight_kg FROM orders WHERE status IN ('PENDING', 'PROCESSING') LIMIT 5;"
        ))
    order_ids = [o["id"] for o in orders[:5]]
    vehicles = get_vehicles()

    # So sánh chi phí giữa xe Diesel và xe Điện EV (nếu có)
    comparisons = []
    for v in vehicles:
        if v["status"] == "Maintenance":
            continue
        res = optimize_routes_for_orders(order_ids, vehicle_id=v["id"], enforce_time_window=True, save_to_db=False)
        if res:
            comparisons.append({
                "vehicle": v,
                "result": res,
            })

    best = min(comparisons, key=lambda x: x["result"]["total_cost_vnd"]) if comparisons else None
    return {
        "agent": "Route Optimization Agent",
        "trace": (
            f"Quét {len(order_ids)} đơn tuyến {province_filter}; kiểm tra tải trọng & giờ cấm tải "
            f"{config.RESTRICTED_TIME_WINDOW[0]}–{config.RESTRICTED_TIME_WINDOW[1]} (giá xăng {config.FUEL_PRICE_PER_LITER:,} đ/L)."
        ),
        "order_ids": order_ids,
        "comparisons": comparisons,
        "best": best,
    }

