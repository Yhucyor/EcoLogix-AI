"""
Agent 4: Route Optimization Agent (CVRPTW & Fleet Comparison)
Tối ưu hóa hành trình xe giao hàng có ràng buộc tải trọng, khung giờ cấm tải và so sánh đội xe.
Tuân thủ chặt chẽ tính khả thi: Loại bỏ xe quá tải, không tráo đổi địa bàn, so sánh FIFO chuẩn xác.
"""
import importlib
import uuid
from typing import Optional, List, Dict, Any
from backend import config
from backend.database.connection import execute_query, rows_to_dicts
from backend.services.routing_service import get_vehicles, optimize_routes_for_orders


def run_route_agent(
    province_filter: Optional[str] = None,
    order_ids: Optional[List[int]] = None,
    requested_limit: Optional[int] = None,
    company_id: int = 1,
    snapshot_ref: Optional[str] = None,
) -> Dict[str, Any]:
    importlib.reload(config)
    snap = snapshot_ref or f"SNAP-{uuid.uuid4().hex[:8].upper()}"

    # 1. Thu thập danh sách đơn hàng
    if order_ids:
        placeholders = ",".join(["?"] * len(order_ids))
        orders = rows_to_dicts(execute_query(
            f"""
            SELECT o.id, o.order_code, o.total_weight_kg, c.province, c.district
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.id IN ({placeholders}) AND o.company_id = ?;
            """,
            (*order_ids, company_id),
        ))
    elif province_filter:
        clean_prov = province_filter.strip()
        orders = rows_to_dicts(execute_query(
            """
            SELECT o.id, o.order_code, o.total_weight_kg, c.province, c.district
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status IN ('PENDING', 'PROCESSING', 'SHIPPING')
              AND LOWER(c.province) LIKE LOWER(?)
              AND o.company_id = ?
            ORDER BY o.id ASC;
            """,
            (f"%{clean_prov}%", company_id),
        ))
    else:
        orders = rows_to_dicts(execute_query(
            """
            SELECT o.id, o.order_code, o.total_weight_kg, c.province, c.district
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status IN ('PENDING', 'PROCESSING')
              AND o.company_id = ?
            ORDER BY o.id ASC
            LIMIT ?;
            """,
            (company_id, requested_limit or 5),
        ))

    total_found = len(orders)
    # Kiểm tra số lượng yêu cầu so với thực tế (Không tráo đổi địa bàn khác)
    if requested_limit and total_found < requested_limit:
        if total_found == 0:
            target_scope = f"tỉnh {province_filter}" if province_filter else "hệ thống"
            return {
                "agent": "Route Optimization Agent",
                "status": "no_orders_found",
                "orders_found": 0,
                "requested_limit": requested_limit,
                "province": province_filter,
                "snapshot_ref": snap,
                "trace": f"Không tìm thấy đơn hàng nào thuộc {target_scope} của doanh nghiệp.",
                "message": f"Không tìm thấy đơn hàng nào tại {target_scope}. Hệ thống không tự ý lấy đơn từ tỉnh khác.",
                "candidates": [],
                "best": None,
            }

    selected_orders = orders[:requested_limit] if requested_limit else orders
    actual_order_ids = [o["id"] for o in selected_orders]
    total_load_kg = sum(float(o.get("total_weight_kg") or 0.0) for o in selected_orders)

    vehicles = get_vehicles(company_id=company_id)
    candidates: List[Dict[str, Any]] = []

    for v in vehicles:
        if v.get("status") == "Maintenance":
            continue
        v_cap = float(v.get("max_load_kg") or config.MAX_VEHICLE_LOAD_KG)
        is_overloaded = total_load_kg > v_cap

        res = optimize_routes_for_orders(
            actual_order_ids,
            vehicle_id=v["id"],
            enforce_time_window=True,
            save_to_db=False,
            company_id=company_id,
        )
        if not res:
            continue

        c_id = f"CAND-{v['id']}-{snap[-4:]}"
        is_feasible = (not is_overloaded) and (res.get("is_feasible", True))
        infeasible_reasons = []
        if is_overloaded:
            infeasible_reasons.append(f"Quá tải: Tổng tải {total_load_kg:.1f} kg vượt quá sức chứa xe {v_cap:.1f} kg")
        if res.get("late_stops", 0) > 0:
            infeasible_reasons.append(f"Trễ hẹn {res['late_stops']} điểm dừng")

        cand = {
            "candidate_id": c_id,
            "snapshot_ref": snap,
            "vehicle": v,
            "vehicle_id": v["id"],
            "max_load_kg": v_cap,
            "total_load_kg": total_load_kg,
            "is_feasible": is_feasible,
            "infeasible_reasons": infeasible_reasons,
            "result": res,
            "distance_km": res["total_distance_km"],
            "baseline_distance_km": res["baseline_distance_km"],
            "total_cost_vnd": res["total_cost_vnd"],
            "co2_emission_kg": res["co2_emission_kg"],
            "saved_distance_km": res["saved_distance_km"],
            "saved_money_vnd": res["saved_money_vnd"],
            "saved_co2_kg": res["saved_co2_kg"],
            "distance_source": res.get("distance_source", "estimated"),
        }
        candidates.append(cand)

    # Lọc ứng viên khả thi: Xe quá tải BỊ LOẠI BỎ hoàn toàn
    feasible_candidates = [c for c in candidates if c["is_feasible"]]
    best = min(feasible_candidates, key=lambda x: (x["total_cost_vnd"], x["co2_emission_kg"])) if feasible_candidates else None

    status = "completed" if best else ("no_feasible_plan" if candidates else "no_orders_found")
    reason = None
    if not best and candidates:
        reason = f"Tất cả {len(candidates)} phương án xe đều bị loại (tổng đơn {total_load_kg:.1f} kg vượt tải trọng các xe khả dụng)."

    trace_msg = (
        f"Quét {len(actual_order_ids)} đơn (tổng tải {total_load_kg:.1f} kg). "
        f"Đánh giá {len(candidates)} phương án xe ({len(feasible_candidates)} khả thi, {len(candidates) - len(feasible_candidates)} bị loại do quá tải/vi phạm). "
        f"Snap: {snap}."
    )

    return {
        "agent": "Route Optimization Agent",
        "status": status,
        "reason": reason,
        "snapshot_ref": snap,
        "order_ids": actual_order_ids,
        "orders_found": total_found,
        "requested_limit": requested_limit,
        "province": province_filter,
        "trace": trace_msg,
        "candidates": candidates,
        "feasible_candidates": feasible_candidates,
        "best": best,
    }
