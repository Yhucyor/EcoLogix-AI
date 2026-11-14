"""
Agent 2: Demand Forecasting Agent (LightGBM Time-Series)
Dự báo nhu cầu hàng hóa chính xác theo đúng SKU và số ngày (horizon_days) yêu cầu.
Không hardcode 30 ngày, không tự ý đổi SKU mặc định, phân biệt thiếu dữ liệu với số đo thực.
"""
from typing import Optional, Dict, Any
from backend.database.connection import execute_query, rows_to_dicts
from backend.services.forecasting_service import get_forecast_for_product, get_regional_demand_distribution


def run_demand_agent(
    horizon_days: int = 30,
    product_id: Optional[int] = None,
    sku_code: Optional[str] = None,
    company_id: int = 1,
) -> Dict[str, Any]:
    # 1. Tìm sản phẩm mục tiêu theo SKU hoặc ID
    target_prod = None
    if sku_code:
        clean_sku = sku_code.strip()
        rows = rows_to_dicts(execute_query(
            "SELECT id, sku, name, unit FROM products WHERE LOWER(sku) = LOWER(?) AND company_id = ?;",
            (clean_sku, company_id),
        ))
        if not rows:
            # Tìm kiếm gần đúng theo mã SKU
            rows = rows_to_dicts(execute_query(
                "SELECT id, sku, name, unit FROM products WHERE LOWER(sku) LIKE LOWER(?) AND company_id = ? LIMIT 1;",
                (f"%{clean_sku}%", company_id),
            ))
        if rows:
            target_prod = rows[0]
        else:
            return {
                "agent": "Demand Forecasting Agent",
                "status": "not_found",
                "error_code": "SKU_NOT_FOUND",
                "message": f"Không tìm thấy mã sản phẩm '{sku_code}' trong doanh nghiệp của bạn.",
                "trace": f"Truy vấn SKU '{sku_code}' thất bại: không tồn tại.",
                "primary_forecast": None,
            }
    elif product_id:
        rows = rows_to_dicts(execute_query(
            "SELECT id, sku, name, unit FROM products WHERE id = ? AND company_id = ?;",
            (product_id, company_id),
        ))
        if rows:
            target_prod = rows[0]
        else:
            return {
                "agent": "Demand Forecasting Agent",
                "status": "not_found",
                "error_code": "PRODUCT_NOT_FOUND",
                "message": f"Không tìm thấy sản phẩm có ID #{product_id} trong doanh nghiệp của bạn.",
                "trace": f"Truy vấn Product ID #{product_id} thất bại.",
                "primary_forecast": None,
            }
    else:
        # Lấy sản phẩm đầu tiên của công ty
        prods = rows_to_dicts(execute_query(
            "SELECT id, sku, name, unit FROM products WHERE company_id = ? ORDER BY id ASC LIMIT 1;",
            (company_id,),
        ))
        if prods:
            target_prod = prods[0]
        else:
            return {
                "agent": "Demand Forecasting Agent",
                "status": "insufficient_data",
                "error_code": "NO_PRODUCTS",
                "message": "Doanh nghiệp hiện chưa có sản phẩm nào trong cơ sở dữ liệu.",
                "trace": "Không có sản phẩm để dự báo.",
                "primary_forecast": None,
            }

    # 2. Chạy mô hình dự báo LightGBM cho đúng horizon_days
    actual_horizon = max(1, min(90, int(horizon_days)))
    fc = get_forecast_for_product(target_prod["id"], horizon_days=actual_horizon)
    if not fc or "df_fut" not in fc:
        return {
            "agent": "Demand Forecasting Agent",
            "status": "failed",
            "error_code": "FORECAST_ERROR",
            "message": f"Không thể tạo dự báo cho sản phẩm {target_prod['name']}.",
            "trace": f"Lỗi tính toán dự báo LightGBM cho SKU {target_prod['sku']}.",
            "primary_forecast": None,
        }

    # Rút trích danh sách điểm dự báo
    points = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "forecast": int(row["forecast"]),
            "lower": int(row["lower"]),
            "upper": int(row["upper"]),
        }
        for _, row in fc["df_fut"].iterrows()
    ]

    trace_msg = (
        f"Chạy {fc['model_name']} cho {target_prod['name']} (`{target_prod['sku']}`) "
        f"kỳ {actual_horizon} ngày (Độ chính xác: {fc['accuracy_pct']}%, WAPE: {fc.get('wape_pct')}%). "
        f"Tổng cầu dự báo: {fc['total_forecast']:,} {target_prod['unit']}."
    )

    regions = get_regional_demand_distribution(company_id=company_id)

    return {
        "agent": "Demand Forecasting Agent",
        "status": "completed",
        "product_id": target_prod["id"],
        "sku": target_prod["sku"],
        "product_name": target_prod["name"],
        "unit": target_prod["unit"],
        "horizon_days": actual_horizon,
        "points_count": len(points),
        "forecast_points": points,
        "primary_forecast": fc,
        "regions": regions,
        "trace": trace_msg,
    }
