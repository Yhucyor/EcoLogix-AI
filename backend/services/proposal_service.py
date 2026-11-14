"""
EcoLogix AI - Proposal Service (PR 6: Human-in-the-Loop & Idempotency)
Quản lý vòng đời đề xuất (Route & Purchase Order):
- Tạo đề xuất có phiên bản (version), thời hạn (expires_at), snapshot_ref và candidate_id.
- Phê duyệt / Từ chối với kiểm soát RBAC, kiểm tra tính tươi mới (Stale Detection).
- Áp dụng trong một transaction duy nhất, chống tạo chuyến trùng (Idempotent).
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from backend.database.connection import get_db, execute_query, execute_insert, execute_update, rows_to_dicts
from backend.utils.helpers import log_activity


def create_proposal(
    company_id: int,
    user_id: int,
    thread_id: str,
    run_id: str,
    proposal_type: str,
    summary: str,
    payload: Dict[str, Any],
    candidate_id: Optional[str] = None,
    snapshot_ref: Optional[str] = None,
    expires_hours: int = 24,
) -> Dict[str, Any]:
    code = f"PROP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).strftime("%Y-%m-%d %H:%M:%S")
    payload_str = json.dumps(payload, ensure_ascii=False)

    p_id = execute_insert(
        """
        INSERT INTO agent_proposals (proposal_code, company_id, user_id, thread_id, run_id, proposal_type,
                                    candidate_id, snapshot_ref, status, version, expires_at, summary, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 1, ?, ?, ?);
        """,
        (code, company_id, user_id, thread_id, run_id, proposal_type, candidate_id, snapshot_ref, expires_at, summary, payload_str),
    )

    return {
        "id": p_id,
        "proposal_code": code,
        "proposal_type": proposal_type,
        "status": "PENDING",
        "version": 1,
        "summary": summary,
        "candidate_id": candidate_id,
        "snapshot_ref": snapshot_ref,
        "expires_at": expires_at,
        "payload": payload,
    }


def get_proposal_by_id(proposal_id: int, company_id: int) -> Optional[Dict[str, Any]]:
    rows = rows_to_dicts(execute_query(
        """
        SELECT * FROM agent_proposals
        WHERE id = ? AND company_id = ?;
        """,
        (proposal_id, company_id),
    ))
    if not rows:
        return None
    p = rows[0]
    try:
        p["payload"] = json.loads(p["payload_json"])
    except Exception:
        p["payload"] = {}
    if p.get("result_json"):
        try:
            p["result"] = json.loads(p["result_json"])
        except Exception:
            p["result"] = None
    return p


def decide_proposal(
    proposal_id: int,
    action: str,  # 'approve' | 'reject'
    user_id: int,
    user_role: str,
    company_id: int,
    expected_version: int = 1,
    request_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    # 1. Kiểm tra quyền hạn RBAC: Chỉ Admin và Manager được duyệt/từ chối
    if user_role not in ("Admin", "Manager"):
        return False, f"Vai trò '{user_role}' chỉ có quyền xem (Auditor), không có quyền phê duyệt đề xuất.", None

    proposal = get_proposal_by_id(proposal_id, company_id=company_id)
    if not proposal:
        return False, "Không tìm thấy bản đề xuất hoặc bạn không thuộc doanh nghiệp sở hữu.", None

    # Chống trùng lặp (Idempotency): Nếu đã APPROVED với cùng request_id thì trả về kết quả cũ
    if proposal["status"] == "APPROVED":
        if request_id and proposal.get("request_id") == request_id:
            return True, "Đề xuất đã được duyệt trước đó (Idempotent replay).", proposal.get("result")
        return False, "Đề xuất này đã được phê duyệt và áp dụng trước đó.", proposal.get("result")

    if proposal["status"] != "PENDING":
        return False, f"Đề xuất không ở trạng thái chờ duyệt (trạng thái hiện tại: {proposal['status']}).", None

    # Kiểm tra version lạc quan
    if proposal["version"] != expected_version:
        return False, f"Phiên bản đề xuất không khớp (hiện tại: {proposal['version']}, yêu cầu: {expected_version}).", None

    # Kiểm tra thời hạn hiệu lực
    if proposal.get("expires_at"):
        try:
            exp_time = datetime.strptime(proposal["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp_time:
                execute_update("UPDATE agent_proposals SET status = 'STALE' WHERE id = ?;", (proposal_id,))
                return False, "Đề xuất đã hết hạn hiệu lực và chuyển sang trạng thái STALE. Vui lòng tính toán lại.", None
        except Exception:
            pass

    payload = proposal.get("payload") or {}

    # 2. Xử lý từ chối (Reject)
    if action.lower() == "reject":
        execute_update(
            "UPDATE agent_proposals SET status = 'REJECTED', version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (proposal_id,),
        )
        log_activity(user_id, "REJECT_PROPOSAL", "agent_proposals", proposal_id, f"Từ chối đề xuất {proposal['proposal_code']}")
        return True, f"Đã từ chối đề xuất {proposal['proposal_code']}.", None

    # 3. Xử lý phê duyệt (Approve) trong transaction duy nhất
    if action.lower() != "approve":
        return False, f"Hành động '{action}' không hợp lệ. Chỉ chấp nhận 'approve' hoặc 'reject'.", None

    # Kiểm tra tính tươi mới của đơn hàng (Stale Detection)
    if proposal["proposal_type"] == "ROUTE":
        order_ids = payload.get("order_ids") or [s["id"] for s in payload.get("stops", []) if s.get("id")]
        if order_ids:
            placeholders = ",".join(["?"] * len(order_ids))
            stale_orders = rows_to_dicts(execute_query(
                f"""
                SELECT id, order_code, status FROM orders
                WHERE id IN ({placeholders}) AND status NOT IN ('PENDING', 'PROCESSING');
                """,
                tuple(order_ids),
            ))
            if stale_orders:
                execute_update("UPDATE agent_proposals SET status = 'STALE' WHERE id = ?;", (proposal_id,))
                stale_codes = ", ".join(o["order_code"] for o in stale_orders)
                return False, f"Đơn hàng ({stale_codes}) đã thay đổi trạng thái sau khi xem trước. Đề xuất đã chuyển sang STALE. Vui lòng tính toán lại.", None

    with get_db() as conn:
        cur = conn.cursor()
        try:
            result_data: Dict[str, Any] = {}

            if proposal["proposal_type"] == "ROUTE":
                # Áp dụng tuyến vận tải
                route_code = payload.get("route_code") or f"RT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                veh_id = payload.get("vehicle_id")
                stops = payload.get("stops") or payload.get("ordered_stops") or []

                cur.execute(
                    """
                    INSERT INTO routes (company_id, route_code, vehicle_id, route_date, status, total_distance_km,
                                        baseline_distance_km, saved_distance_km, total_time_hours, fuel_consumed_liters,
                                        fuel_saved_liters, co2_emission_kg, saved_co2_kg, total_cost_vnd, saved_cost_vnd, is_optimized)
                    VALUES (?, ?, ?, ?, 'Optimized', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                    """,
                    (
                        company_id,
                        route_code,
                        veh_id,
                        datetime.now().strftime("%Y-%m-%d"),
                        payload.get("total_distance_km", 0.0),
                        payload.get("baseline_distance_km", 0.0),
                        payload.get("saved_distance_km", 0.0),
                        payload.get("total_time_hours", 1.0),
                        payload.get("fuel_needed_liters", 0.0),
                        payload.get("saved_fuel_liters", 0.0),
                        payload.get("co2_emission_kg", 0.0),
                        payload.get("saved_co2_kg", 0.0),
                        payload.get("total_cost_vnd", 0.0),
                        payload.get("saved_money_vnd", 0.0),
                    ),
                )
                r_id = cur.lastrowid

                # Lưu route_stops
                for idx, stp in enumerate(stops, 1):
                    cur.execute(
                        """
                        INSERT INTO route_stops (route_id, order_id, stop_sequence, arrival_time, departure_time, lat, lng, address)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            r_id,
                            stp.get("id") or stp.get("order_id"),
                            idx,
                            stp.get("arrival_time", "08:00"),
                            stp.get("departure_time", "08:15"),
                            stp.get("lat"),
                            stp.get("lng"),
                            stp.get("address", ""),
                        ),
                    )

                # Lưu carbon_emissions
                cur.execute(
                    """
                    INSERT INTO carbon_emissions (route_id, co2_kg, fuel_liters, calculation_date, standard)
                    VALUES (?, ?, ?, ?, 'GHG Protocol Scope 1');
                    """,
                    (
                        r_id,
                        payload.get("co2_emission_kg", 0.0),
                        payload.get("fuel_needed_liters", 0.0),
                        datetime.now().strftime("%Y-%m-%d"),
                    ),
                )

                # Chuyển trạng thái đơn hàng sang SHIPPING
                order_ids = [s.get("id") or s.get("order_id") for s in stops if s.get("id") or s.get("order_id")]
                if order_ids:
                    pl = ",".join(["?"] * len(order_ids))
                    cur.execute(
                        f"UPDATE orders SET status = 'SHIPPING' WHERE id IN ({pl}) AND company_id = ?;",
                        (*order_ids, company_id),
                    )

                result_data = {
                    "route_id": r_id,
                    "route_code": route_code,
                    "stops_count": len(stops),
                    "total_distance_km": payload.get("total_distance_km", 0.0),
                    "saved_money_vnd": payload.get("saved_money_vnd", 0.0),
                    "saved_co2_kg": payload.get("saved_co2_kg", 0.0),
                }

            elif proposal["proposal_type"] == "PURCHASE_ORDER":
                # Áp dụng Lệnh nhập kho PO nháp
                prod_id = payload.get("product_id")
                qty = payload.get("quantity", 0)
                wh_id = payload.get("warehouse_id", 1)
                po_ref = payload.get("po_ref") or f"PO-{datetime.now().strftime('%Y%m%d-%H%M')}"

                cur.execute(
                    """
                    INSERT INTO inventory_transactions (warehouse_id, product_id, transaction_type, quantity,
                                                        transaction_date, reference_code, user_id, notes)
                    VALUES (?, ?, 'IN_PENDING', ?, CURRENT_TIMESTAMP, ?, ?, 'Đề xuất PO từ AI đã duyệt (chờ thực nhận)');
                    """,
                    (wh_id, prod_id, qty, po_ref, user_id),
                )
                result_data = {
                    "po_ref": po_ref,
                    "product_id": prod_id,
                    "quantity": qty,
                    "warehouse_id": wh_id,
                    "status": "APPROVED",
                }

            # Cập nhật proposal status -> APPROVED
            cur.execute(
                """
                UPDATE agent_proposals
                SET status = 'APPROVED', version = version + 1, result_json = ?, request_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (json.dumps(result_data, ensure_ascii=False), request_id, proposal_id),
            )
            conn.commit()

            log_activity(user_id, "APPROVE_PROPOSAL", "agent_proposals", proposal_id, f"Phê duyệt đề xuất {proposal['proposal_code']}")
            return True, f"Đã phê duyệt và áp dụng thành công đề xuất {proposal['proposal_code']}!", result_data

        except Exception as e:
            conn.rollback()
            return False, f"Lỗi transaction khi áp dụng đề xuất: {str(e)}", None
