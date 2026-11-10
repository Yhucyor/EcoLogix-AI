"""Agent 3: Inventory Management Agent (Real-Time WMS & Safety Stock)."""
from backend.services.inventory_service import get_inventory_status, get_all_warehouses, get_inventory_metrics


def run_inventory_agent(search_term: str = "") -> dict:
    warehouses = get_all_warehouses()
    items = get_inventory_status(search=search_term)
    metrics = get_inventory_metrics()
    low_items = [r for r in items if r["quantity"] <= r["safety_stock"]]

    return {
        "agent": "Inventory Management Agent",
        "trace": f"Truy vấn {len(warehouses)} kho hàng và {len(items)} dòng tồn kho SKU; phát hiện {len(low_items)} mục dưới ngưỡng Safety Stock.",
        "warehouses": warehouses,
        "items": items,
        "low_items": low_items,
        "metrics": metrics,
    }

