"""
Agent 3: Inventory Management Agent (Real-Time WMS & Safety Stock)
Quản lý tồn kho thời gian thực, đối soát ngưỡng an toàn Safety Stock và phát hiện đứt gãy hàng.
"""
from typing import Optional, Dict, Any, List
from backend.database.connection import execute_query, rows_to_dicts
from backend.services.inventory_service import get_inventory_status, get_all_warehouses, get_inventory_metrics


def run_inventory_agent(
    search_term: str = "",
    sku_code: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    warehouse_name: Optional[str] = None,
    company_id: int = 1,
) -> Dict[str, Any]:
    warehouses = get_all_warehouses(company_id=company_id)
    all_items = get_inventory_status(search=search_term, company_id=company_id)
    metrics = get_inventory_metrics(company_id=company_id)

    # Lọc kho nếu có
    target_wh = None
    if warehouse_id:
        target_wh = next((w for w in warehouses if w["id"] == warehouse_id), None)
    elif warehouse_name:
        clean_wh = warehouse_name.strip().lower()
        target_wh = next((w for w in warehouses if clean_wh in w["name"].lower() or clean_wh in (w.get("code") or "").lower()), None)

    filtered_items = all_items
    if target_wh:
        filtered_items = [it for it in filtered_items if it.get("warehouse_id") == target_wh["id"]]

    # Lọc SKU nếu có
    target_item = None
    if sku_code:
        clean_sku = sku_code.strip().lower()
        filtered_items = [it for it in filtered_items if clean_sku in it.get("sku", "").lower() or clean_sku in it.get("product_name", "").lower()]
        if filtered_items:
            target_item = filtered_items[0]

    low_items = [r for r in filtered_items if r["quantity"] <= r["safety_stock"]]

    trace_msg = (
        f"Truy vấn {len(warehouses)} kho và {len(filtered_items)} dòng hàng "
        + (f"tại kho '{target_wh['name']}' " if target_wh else "")
        + (f"cho SKU '{sku_code}' " if sku_code else "")
        + f"(Phát hiện {len(low_items)} mục dưới ngưỡng an toàn)."
    )

    return {
        "agent": "Inventory Management Agent",
        "status": "completed",
        "trace": trace_msg,
        "warehouse": target_wh,
        "target_item": target_item,
        "items": filtered_items,
        "low_items": low_items,
        "warehouses": warehouses,
        "metrics": metrics,
    }
