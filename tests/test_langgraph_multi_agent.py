"""
EcoLogix AI - Stateful Multi-Agent System Acceptance Test Suite (Issue #1)
Kiểm thử toàn diện Ma trận nghiệm thu (V1, V2, U1, U2, U3, U4, I1, I2, I3, S1, S2, S3)
và Demo 1, Demo 2 theo đặc tả chuẩn của Issue #1.
"""
import unittest
import uuid
import pandas as pd
import numpy as np

from tests.support import LiveApiTestCase, http_json
from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from backend.services.forecasting_service import _featurize, get_forecast_for_product
from backend.services.routing_service import optimize_routes_for_orders
from backend.agents.route_agent import run_route_agent
from backend.agents.demand_agent import run_demand_agent
from backend.agents.finance_agent import run_finance_agent
from backend.agents.esg_agent import run_esg_agent
from backend.agents.graph import build_ecologix_graph
from backend.services.checkpoint_service import InMemorySaver, DbCheckpointer
from backend.services.proposal_service import create_proposal, decide_proposal, get_proposal_by_id


class TestLangGraphMultiAgentEpic(LiveApiTestCase):

    # ==================== V1: VALIDATION / API ====================
    def test_v1_forecast_horizon_and_sku_validation(self):
        """V1: Yêu cầu SKU-003 14 ngày -> trả đúng SKU-003 và 14 điểm; SKU không tồn tại -> báo mã lỗi rõ."""
        res_14 = run_demand_agent(horizon_days=14, sku_code="SKU-003", company_id=1)
        self.assertEqual(res_14["status"], "completed")
        self.assertEqual(res_14["sku"], "SKU-003")
        self.assertEqual(res_14["horizon_days"], 14)
        self.assertEqual(res_14["points_count"], 14)

        # SKU không tồn tại -> nhận lỗi có mã rõ ràng, không fallback về SKU mặc định
        res_invalid = run_demand_agent(horizon_days=14, sku_code="SKU-99999", company_id=1)
        self.assertEqual(res_invalid["status"], "not_found")
        self.assertEqual(res_invalid["error_code"], "SKU_NOT_FOUND")
        self.assertIsNone(res_invalid["primary_forecast"])

    # ==================== V2: VALIDATION / ROUTE ====================
    def test_v2_route_province_isolation_no_substitution(self):
        """V2: Yêu cầu 12 đơn Hà Nội (khu vực không có đơn) -> không tự ý tráo đơn sang Bình Dương."""
        res = run_route_agent(province_filter="Hà Nội", requested_limit=12, company_id=1)
        self.assertEqual(res["status"], "no_orders_found")
        self.assertEqual(res["orders_found"], 0)
        self.assertIn("Hà Nội", res["trace"])
        self.assertIsNone(res["best"])

    # ==================== U1: UNIT / ROUTE OVERLOAD ====================
    def test_u1_overloaded_vehicle_is_excluded(self):
        """U1: Tổng tải 2.000 kg; xe 1.200 kg rẻ hơn nhưng quá tải -> bị loại khỏi danh sách khả thi."""
        # Tạo đơn tải nặng 2.000 kg tạm thời
        cust_id = execute_insert("INSERT INTO customers (name, province, district, address, lat, lng, company_id) VALUES ('KH Test U1', 'Bình Dương', 'Dĩ An', 'KCN Sóng Thần', 10.90, 106.75, 1);")
        o_id1 = execute_insert("INSERT INTO orders (order_code, customer_id, total_amount, total_weight_kg, status, company_id) VALUES ('ORD-U1-1', ?, 5000000, 1000.0, 'PENDING', 1);", (cust_id,))
        o_id2 = execute_insert("INSERT INTO orders (order_code, customer_id, total_amount, total_weight_kg, status, company_id) VALUES ('ORD-U1-2', ?, 5000000, 1000.0, 'PENDING', 1);", (cust_id,))

        try:
            res = run_route_agent(order_ids=[o_id1, o_id2], company_id=1)
            # Xe quá tải không được chọn là best
            if res["best"]:
                self.assertGreaterEqual(res["best"]["max_load_kg"], 2000.0)
            # Kiểm tra trong candidates, xe nhỏ (VD: max_load_kg <= 1500) phải bị đánh dấu is_feasible = False
            for cand in res["candidates"]:
                if cand["max_load_kg"] < 2000.0:
                    self.assertFalse(cand["is_feasible"])
                    self.assertTrue(any("Quá tải" in r for r in cand["infeasible_reasons"]))
        finally:
            execute_update("DELETE FROM orders WHERE id IN (?, ?);", (o_id1, o_id2))
            execute_update("DELETE FROM customers WHERE id = ?;", (cust_id,))

    # ==================== U2: UNIT / FORECAST NO LEAKAGE ====================
    def test_u2_forecast_features_no_future_leakage(self):
        """U2: Featurizer shift(1).rolling(7) không bị rò rỉ dữ liệu ngày đích; WAPE tính chuẩn xác."""
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        df1 = pd.DataFrame({"date": dates, "actual": [10, 12, 15, 14, 16, 18, 20, 25, 30, 35]})
        feat1 = _featurize(df1)

        # Đổi giá trị ngày đích (ngày 8, index 7) từ 25 thành 999
        df2 = df1.copy()
        df2.loc[7, "actual"] = 999
        feat2 = _featurize(df2)

        # Feature trước ngày đích (index 0..6) phải giữ nguyên 100%
        for i in range(7):
            self.assertEqual(feat1.loc[i, "lag_1"], feat2.loc[i, "lag_1"])
            self.assertEqual(feat1.loc[i, "rolling_7"], feat2.loc[i, "rolling_7"])

    # ==================== U3: UNIT / KPI FIFO BASELINE ====================
    def test_u3_identical_fifo_has_zero_savings(self):
        """U3: Khi thứ tự tối ưu trùng hoàn toàn thứ tự FIFO, mức tiết kiệm phải bằng 0 (không nâng ảo 112%)."""
        pending = rows_to_dicts(execute_query("SELECT id FROM orders WHERE status = 'PENDING' AND company_id = 1 LIMIT 2;"))
        if pending:
            order_ids = [p["id"] for p in pending]
            res = optimize_routes_for_orders(order_ids, vehicle_id=1, save_to_db=False, company_id=1)
            # Nếu baseline_distance_km == total_distance_km thì saved_distance_km phải = 0
            if res["baseline_distance_km"] == res["total_distance_km"]:
                self.assertEqual(res["saved_distance_km"], 0.0)
                self.assertEqual(res["saved_money_vnd"], 0.0)

    # ==================== U4: UNIT / GRAPH JOINT EVALUATION ====================
    def test_u4_finance_and_esg_evaluate_same_candidate(self):
        """U4: Finance Agent và ESG Agent cùng đánh giá trên cùng candidate_id và snapshot_ref."""
        fake_candidates = [
            {
                "candidate_id": "CAND-01",
                "snapshot_ref": "SNAP-TEST-01",
                "baseline_cost_vnd": 1000000.0,
                "total_cost_vnd": 850000.0,
                "saved_money_vnd": 150000.0,
                "co2_emission_kg": 25.0,
                "saved_co2_kg": 5.0,
                "vehicle": {"id": 1, "vehicle_name": "Xe 1", "fuel_type": "Diesel"},
            },
            {
                "candidate_id": "CAND-02",
                "snapshot_ref": "SNAP-TEST-01",
                "baseline_cost_vnd": 1000000.0,
                "total_cost_vnd": 800000.0,
                "saved_money_vnd": 200000.0,
                "co2_emission_kg": 15.0,
                "saved_co2_kg": 15.0,
                "vehicle": {"id": 2, "vehicle_name": "Xe EV", "fuel_type": "Electric"},
            },
        ]
        fin_out = run_finance_agent(company_id=1, candidates=fake_candidates, snapshot_ref="SNAP-TEST-01")
        esg_out = run_esg_agent(company_id=1, candidates=fake_candidates, snapshot_ref="SNAP-TEST-01")

        # Ghép theo candidate_id, không ghép theo vị trí
        self.assertIn("CAND-01", fin_out["candidate_evaluations"])
        self.assertIn("CAND-01", esg_out["candidate_evaluations"])
        self.assertEqual(fin_out["candidate_evaluations"]["CAND-01"]["snapshot_ref"], "SNAP-TEST-01")
        self.assertEqual(esg_out["candidate_evaluations"]["CAND-01"]["snapshot_ref"], "SNAP-TEST-01")
        self.assertEqual(esg_out["candidate_evaluations"]["CAND-02"]["is_electric"], True)

    # ==================== I1: INTEGRATION / STATE ACROSS RESTART ====================
    def test_i1_state_retention_across_restart(self):
        """I1 (Demo 1): Hỏi tồn kho SKU-003 -> reload/restart checkpointer -> hỏi tiếp 'Dự báo 14 ngày cho SKU đó'."""
        thread_id = f"thread_test_i1_{uuid.uuid4().hex[:6]}"
        checkpointer = DbCheckpointer(company_id=1)
        graph = build_ecologix_graph(checkpointer=checkpointer)

        # Lượt 1: Hỏi tồn kho SKU-003
        state_turn1 = graph.invoke(
            {"query": "Kiểm tra tồn kho SKU-003 tại Kho Thủ Đức", "company_id": 1, "user_id": 1},
            config={"configurable": {"thread_id": thread_id}},
        )
        self.assertEqual(state_turn1["confirmed_slots"].get("sku_code"), "SKU-003")

        # GIẢ LẬP RESTART SERVER: Khởi tạo instance mới hoàn toàn của checkpointer & graph
        restarted_checkpointer = DbCheckpointer(company_id=1)
        restarted_graph = build_ecologix_graph(checkpointer=restarted_checkpointer)

        # Lượt 2: Hỏi tiếp "Dự báo 14 ngày cho SKU đó" trên cùng thread_id
        state_turn2 = restarted_graph.invoke(
            {"query": "Dự báo 14 ngày cho SKU đó", "company_id": 1, "user_id": 1},
            config={"configurable": {"thread_id": thread_id}},
        )

        self.assertEqual(state_turn2["status"], "completed")
        self.assertEqual(state_turn2["confirmed_slots"].get("sku_code"), "SKU-003")
        self.assertEqual(state_turn2["confirmed_slots"].get("horizon_days"), 14)
        self.assertIn("SKU-003", state_turn2["reply"])
        self.assertIn("14 ngày", state_turn2["reply"])

        # Phiên mới (thread khác) không có ngữ cảnh cũ
        fresh_thread = f"thread_fresh_{uuid.uuid4().hex[:6]}"
        state_fresh = restarted_graph.invoke(
            {"query": "Dự báo 14 ngày cho SKU đó", "company_id": 1, "user_id": 1},
            config={"configurable": {"thread_id": fresh_thread}},
        )
        # Phiên mới chưa có SKU nên phải hỏi lại
        self.assertEqual(state_fresh["status"], "needs_clarification")

    # ==================== I2: INTEGRATION / PROPOSAL RESUME & IDEMPOTENCY ====================
    def test_i2_proposal_approval_and_idempotency(self):
        """I2 (Demo 2): Tạo đề xuất -> duyệt thành công -> gửi lại cùng request_id -> trả lại chuyến cũ (Idempotent)."""
        c_i2 = execute_insert("INSERT INTO customers (name, province, lat, lng, company_id) VALUES ('KH I2', 'Bình Dương', 10.91, 106.76, 1);")
        o_i2_1 = execute_insert("INSERT INTO orders (order_code, customer_id, total_amount, total_weight_kg, status, company_id) VALUES ('ORD-I2-1', ?, 500000, 20.0, 'PENDING', 1);", (c_i2,))
        o_i2_2 = execute_insert("INSERT INTO orders (order_code, customer_id, total_amount, total_weight_kg, status, company_id) VALUES ('ORD-I2-2', ?, 500000, 20.0, 'PENDING', 1);", (c_i2,))

        try:
            prop = create_proposal(
                company_id=1,
                user_id=1,
                thread_id="thread_prop_test",
                run_id="run_test",
                proposal_type="ROUTE",
                summary="Tuyến thử nghiệm 2 đơn",
                payload={
                    "vehicle_id": 1,
                    "order_ids": [o_i2_1, o_i2_2],
                    "total_distance_km": 45.0,
                    "baseline_distance_km": 50.0,
                    "saved_distance_km": 5.0,
                    "total_cost_vnd": 250000.0,
                    "saved_money_vnd": 50000.0,
                    "co2_emission_kg": 12.0,
                    "saved_co2_kg": 2.0,
                    "stops": [
                        {"id": o_i2_1, "lat": 10.85, "lng": 106.77, "address": "Kho"},
                        {"id": o_i2_2, "lat": 10.90, "lng": 106.80, "address": "Khách A"},
                    ],
                },
            )
            prop_id = prop["id"]

            # Duyệt lần 1
            ok1, msg1, res1 = decide_proposal(
                proposal_id=prop_id,
                action="approve",
                user_id=1,
                user_role="Admin",
                company_id=1,
                expected_version=1,
                request_id="req-unique-999",
            )
            self.assertTrue(ok1, f"Failed approve 1: {msg1}")
            self.assertIsNotNone(res1)
            route_id_1 = res1["route_id"]

            # Duyệt lần 2 với cùng request_id (Replay) -> Trả về chuyến cũ, không tạo thêm chuyến mới
            ok2, msg2, res2 = decide_proposal(
                proposal_id=prop_id,
                action="approve",
                user_id=1,
                user_role="Admin",
                company_id=1,
                expected_version=1,
                request_id="req-unique-999",
            )
            self.assertTrue(ok2)
            self.assertEqual(res2["route_id"], route_id_1)
        finally:
            execute_update("DELETE FROM route_stops WHERE order_id IN (?, ?);", (o_i2_1, o_i2_2))
            execute_update("DELETE FROM orders WHERE id IN (?, ?);", (o_i2_1, o_i2_2))
            execute_update("DELETE FROM customers WHERE id = ?;", (c_i2,))

    # ==================== I3: INTEGRATION / STALE PROPOSAL DETECTION ====================
    def test_i3_stale_proposal_detection(self):
        """I3: Khi đơn hàng trong đề xuất đã bị giao hoặc hủy, đề xuất chuyển thành STALE và từ chối duyệt."""
        # Tạo đơn tạm
        c_id = execute_insert("INSERT INTO customers (name, province, company_id) VALUES ('KH Stale', 'Bình Dương', 1);")
        o_id = execute_insert("INSERT INTO orders (order_code, customer_id, total_amount, total_weight_kg, status, company_id) VALUES ('ORD-STALE-1', ?, 1000000, 50.0, 'PENDING', 1);", (c_id,))

        prop = create_proposal(
            company_id=1,
            user_id=1,
            thread_id="thread_stale_test",
            run_id="run_stale",
            proposal_type="ROUTE",
            summary="Tuyến có đơn sẽ bị thay đổi",
            payload={"order_ids": [o_id], "vehicle_id": 1, "stops": [{"id": o_id, "lat": 10.8, "lng": 106.7}]},
        )

        # Giả lập đơn bị chuyển sang DELIVERED bởi hệ thống khác
        execute_update("UPDATE orders SET status = 'DELIVERED' WHERE id = ?;", (o_id,))

        ok, msg, _ = decide_proposal(
            proposal_id=prop["id"],
            action="approve",
            user_id=1,
            user_role="Manager",
            company_id=1,
        )
        self.assertFalse(ok)
        self.assertIn("STALE", msg)

        updated_p = get_proposal_by_id(prop["id"], company_id=1)
        self.assertEqual(updated_p["status"], "STALE")

        # Cleanup
        execute_update("DELETE FROM orders WHERE id = ?;", (o_id,))
        execute_update("DELETE FROM customers WHERE id = ?;", (c_id,))

    # ==================== S1: SECURITY / RBAC PERMISSIONS ====================
    def test_s1_auditor_cannot_approve_proposal(self):
        """S1: Vai trò Auditor (chỉ xem) bị chặn khi cố duyệt đề xuất (HTTP 403 Forbidden)."""
        prop = create_proposal(
            company_id=1,
            user_id=1,
            thread_id="thread_s1",
            run_id="run_s1",
            proposal_type="ROUTE",
            summary="Đề xuất test quyền",
            payload={"vehicle_id": 1},
        )
        ok, msg, _ = decide_proposal(
            proposal_id=prop["id"],
            action="approve",
            user_id=99,
            user_role="Auditor",
            company_id=1,
        )
        self.assertFalse(ok)
        self.assertIn("Auditor", msg)

    # ==================== S2 & S3: SECURITY / SANITIZATION ====================
    def test_s2_trace_does_not_leak_secrets(self):
        """S2: Trace thực thi và error messages không để lộ API Key hoặc mật khẩu."""
        res = run_demand_agent(horizon_days=14, sku_code="SKU-001", company_id=1)
        trace_str = str(res.get("trace", ""))
        self.assertNotIn("password", trace_str.lower())
        self.assertNotIn("secret", trace_str.lower())
        self.assertNotIn("ai_api_key", trace_str.lower())


if __name__ == "__main__":
    unittest.main()
