"""Agent 2: Demand Forecasting Agent (LightGBM Time-Series)."""
from backend.database.connection import execute_query
from backend.services.forecasting_service import get_forecast_for_product, get_regional_demand_distribution


def run_demand_agent(horizon_days: int = 30, product_id: int = 1) -> dict:
    prods = execute_query("SELECT id, sku, name FROM products ORDER BY id ASC;")
    if not prods:
        return {"trace": "Không có sản phẩm trong DB.", "summary": "Chưa có dữ liệu SKU."}
    target_id = product_id if any(p["id"] == product_id for p in prods) else prods[0]["id"]
    fc = get_forecast_for_product(target_id, horizon_days=horizon_days)
    regions = get_regional_demand_distribution()

    total_all = 0
    low_items = []
    for p in prods[:3]:
        p_fc = get_forecast_for_product(p["id"], horizon_days=horizon_days)
        total_all += p_fc.get("total_forecast", 0)
        if p_fc.get("suggested_po", 0) > 0:
            low_items.append(f"{p['name']} (đề xuất nhập +{p_fc['suggested_po']:,} {p_fc['product']['unit']})")

    return {
        "agent": "Demand Forecasting Agent",
        "trace": f"Chạy mô hình {fc['model_name']} trên 60 ngày dữ liệu thực tế cho SKU #{target_id} (Độ chính xác {fc['accuracy_pct']}%, MAPE {fc['mape_pct']}%).",
        "primary_forecast": fc,
        "top3_total_demand": total_all,
        "regions": regions,
        "po_alerts": low_items,
    }

