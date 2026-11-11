"""Tests for LightGBM Forecasting + CSV import, CVRPTW Routing, 6 AI Agents, Contact Email, Exporters & Live SPA."""
import os
from unittest.mock import patch

from backend.services.ai_service import clear_conversation, get_conversation_messages, process_agent_query
from backend.services.email_service import get_contact_recipient, send_contact_email
from backend.services.forecasting_service import get_forecast_for_product, import_sales_history_csv
from backend.services.routing_service import (
    _ROAD_GEOMETRY_CACHE,
    get_pending_orders,
    get_road_route_geometry,
    optimize_100_points,
    optimize_routes_for_orders,
)
from tests.support import LiveApiTestCase, http_json, http_request


class TestAnalyticsRoutingAiAndExports(LiveApiTestCase):
    def test_forecasting_csv_import_and_lightgbm(self):
        csv_payload = "date,quantity\n2026-10-01,60\n2026-10-02,65\n2026-10-03,72\n2026-10-04,78\n2026-10-05,80"
        st, body = http_json(
            self.base_url,
            "POST",
            "/api/forecast/import-history",
            {"product_id": 1, "csv_text": csv_payload},
        )
        self.assertEqual(st, 200)
        self.assertEqual(body["imported_days"], 5)

        fc = get_forecast_for_product(1, horizon_days=14, save_history=True)
        self.assertGreater(fc["total_forecast"], 0)
        self.assertGreater(fc["safety_stock"], 0)
        self.assertGreaterEqual(fc["accuracy_pct"], 0)
        self.assertIn("LightGBM", fc["model_name"])

        ok_direct, _, cnt = import_sales_history_csv(1, "date,quantity\n2026-10-06,75")
        self.assertTrue(ok_direct)
        self.assertEqual(cnt, 1)

    def test_vrp_routing_orders_and_100points(self):
        pending = get_pending_orders()
        order_ids = [o["id"] for o in pending[:5]]

        # 1. Auto Ensemble + full solver benchmarks + EV vs Diesel recommendations
        res = optimize_routes_for_orders(order_ids, vehicle_id=1, enforce_time_window=True, save_to_db=False, algorithm="auto")
        self.assertIsNotNone(res)
        self.assertGreater(res["total_distance_km"], 0)
        self.assertEqual(len(res["ordered_stops"]), len(order_ids))
        self.assertEqual(len(res["algorithm_benchmarks"]), 4)
        self.assertGreater(len(res["vehicle_recommendations"]), 0)
        self.assertTrue(any(b["selected"] for b in res["algorithm_benchmarks"]))

        # 2. All explicit solvers work consistently
        for algo in ("clarke_wright", "nn_or_opt", "simulated_annealing"):
            algo_res = optimize_routes_for_orders(order_ids, vehicle_id=1, enforce_time_window=True, save_to_db=False, algorithm=algo)
            self.assertEqual(algo_res["algorithm_used"], algo)
            self.assertEqual(len(algo_res["ordered_stops"]), len(order_ids))
            self.assertGreater(algo_res["total_distance_km"], 0)

        # 3. Multi-vehicle capacity splitting via Clarke-Wright CVRP + SA
        mv_ids = [o["id"] for o in pending]
        mv_res = optimize_routes_for_orders(mv_ids, enforce_time_window=True, save_to_db=False, multi_vehicle=True)
        self.assertTrue(mv_res["multi_vehicle"])
        self.assertGreaterEqual(len(mv_res["multi_vehicle_routes"]), 1)
        self.assertEqual(len(mv_res["ordered_stops"]), len(mv_ids))
        self.assertTrue(all("assigned_vehicle" in s for s in mv_res["ordered_stops"]))

        # 4. Live HTTP POST /api/routing/optimize with Simulated Annealing & multi_vehicle
        st_sa, body_sa = http_json(
            self.base_url,
            "POST",
            "/api/routing/optimize",
            {"mode": "orders", "order_ids": order_ids, "vehicle_id": 1, "enforce_time_window": True, "save_to_db": False, "algorithm": "simulated_annealing", "multi_vehicle": False},
        )
        self.assertEqual(st_sa, 200)
        self.assertEqual(body_sa["result"]["algorithm_used"], "simulated_annealing")

        st_mv, body_mv = http_json(
            self.base_url,
            "POST",
            "/api/routing/optimize",
            {"mode": "orders", "order_ids": mv_ids, "enforce_time_window": True, "save_to_db": False, "multi_vehicle": True},
        )
        self.assertEqual(st_mv, 200)
        self.assertTrue(body_mv["result"]["multi_vehicle"])

        # 5. 100-point (50 & 100 scope) Clarke-Wright + 2-Opt/Or-Opt check
        pts50 = optimize_100_points(scope_count=50, enforce_avoidance=True)
        self.assertEqual(pts50["total_points"], 50)
        self.assertEqual(set(pts50["routes"].keys()), {"XE-01", "XE-02", "XE-03"})
        self.assertIn("Clarke-Wright", pts50["algorithm_name"])
        self.assertEqual(set(pts50["metrics_by_vehicle"].keys()), {"XE-01", "XE-02", "XE-03"})

        st_100, body_100 = http_json(
            self.base_url,
            "POST",
            "/api/routing/optimize",
            {"mode": "100points", "scope_count": 100, "enforce_time_window": True},
        )
        self.assertEqual(st_100, 200)
        self.assertEqual(body_100["result"]["total_points"], 100)
        self.assertIn("geometry", res)
        self.assertGreaterEqual(len(res["geometry"]), 2)

        # 6. Road geometry snapping endpoint + OSRM chunking/caching verification
        pts_req = [{"lat": 10.8505, "lng": 106.7718}, {"lat": 10.7769, "lng": 106.7009}, {"lat": 10.8505, "lng": 106.7718}]
        st_geo, body_geo = http_json(self.base_url, "POST", "/api/routing/road-geometry", {"coordinates": pts_req})
        self.assertEqual(st_geo, 200)
        self.assertTrue(body_geo["ok"])
        self.assertEqual(len(body_geo["points"]), 3)

        st_over, _ = http_json(
            self.base_url,
            "POST",
            "/api/routing/road-geometry",
            {"coordinates": [{"lat": 10.8, "lng": 106.7}] * 151},
        )
        self.assertEqual(st_over, 400)

        mock_osrm = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 14250.0,
                    "geometry": {
                        "coordinates": [
                            [106.7718, 10.8505],
                            [106.7420, 10.8120],
                            [106.7009, 10.7769],
                        ]
                    },
                }
            ],
        }
        _ROAD_GEOMETRY_CACHE.clear()
        with patch.dict(os.environ, {"ECOLOGIX_DISABLE_OSRM": ""}):
            with patch("backend.services.routing_service._fetch_osrm_json", return_value=mock_osrm) as m_osrm:
                # 25 unique waypoints forces 2 chunks (20 + 6 overlapping)
                many_pts = [(10.75 + i * 0.005, 106.66 + i * 0.004) for i in range(25)]
                snapped = get_road_route_geometry(many_pts)
                self.assertTrue(snapped["snapped"])
                self.assertEqual(m_osrm.call_count, 2)
                self.assertEqual(snapped["points"][0], [10.8505, 106.7718])
                # Cached second call hits memory cache without another OSRM call
                cached_snapped = get_road_route_geometry(many_pts)
                self.assertEqual(m_osrm.call_count, 2)
                self.assertEqual(cached_snapped["points"], snapped["points"])
        _ROAD_GEOMETRY_CACHE.clear()

    def test_ai_chat_and_clear_history_endpoint(self):
        trace, content, _ = process_agent_query("Kho hàng hiện còn bao nhiêu sản phẩm?", user_id=1, save_to_db=True)
        self.assertTrue(len(content) > 10)
        self.assertGreater(len(trace), 0)
        self.assertGreater(len(get_conversation_messages(user_id=1)), 0)

        del_status, del_body = http_json(self.base_url, "DELETE", "/api/ai/messages?user_id=1")
        self.assertEqual(del_status, 200)
        self.assertTrue(del_body["ok"])

        msgs_status, msgs_body = http_json(self.base_url, "GET", "/api/ai/messages?user_id=1")
        self.assertEqual(msgs_status, 200)
        self.assertEqual(len(msgs_body["messages"]), 0)
        self.assertTrue(clear_conversation(1))

    def test_reports_pdf_xlsx_exports_and_spa_routes(self):
        pdf_status, pdf_headers, pdf_bytes = http_request(self.base_url, "GET", "/api/reports/export/pdf")
        self.assertEqual(pdf_status, 200)
        self.assertIn("application/pdf", pdf_headers.get("content-type", ""))
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1."))

        xlsx_status, _, xlsx_bytes = http_request(self.base_url, "GET", "/api/reports/export/xlsx")
        self.assertEqual(xlsx_status, 200)
        self.assertTrue(xlsx_bytes.startswith(b"PK"))

        for path in ("/", "/login", "/register", "/dashboard", "/inventory", "/forecasting", "/orders", "/routing", "/components/common.jsx", "/pages/App.jsx"):
            st, _, raw = http_request(self.base_url, "GET", path)
            self.assertEqual(st, 200, f"Expected HTTP 200 for {path}")
            self.assertGreater(len(raw), 100)

    def test_contact_faq_email_and_smtp_fallback(self):
        self.assertEqual(get_contact_recipient(), "geroolyhuicy@gmail.com")

        # Live POST /api/contact without SMTP credentials falls back transparently with mailto + gmail links
        st, body = http_json(
            self.base_url,
            "POST",
            "/api/contact",
            {
                "name": "Công ty Test\r\nBcc: evil@example.com",
                "contact": "khachhang@example.com",
                "need": "Hỏi đáp kỹ thuật / FAQ",
                "message": "Cần tư vấn tích hợp VRP cho 12 xe tải.",
                "source": "FAQ",
            },
        )
        self.assertEqual(st, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["recipient"], "geroolyhuicy@gmail.com")
        self.assertFalse(body["email_sent"])
        self.assertIn("mailto:geroolyhuicy@gmail.com?", body["mailto_url"])
        self.assertIn("https://mail.google.com/mail/", body["gmail_compose_url"])

        # Mocked real SMTP delivery when SMTP credentials are configured
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "sender@gmail.com",
                "SMTP_PASSWORD": "app-password-demo",
            },
        ), patch("backend.services.email_service.smtplib.SMTP") as mock_smtp:
            res = send_contact_email(
                name="Anh Minh",
                contact="anhminh@company.vn",
                need="Dùng thử miễn phí 14 ngày",
                message="Muốn demo 1-1.",
            )
            self.assertTrue(res["email_sent"])
            self.assertEqual(res["mode"], "smtp")
            self.assertEqual(res["recipient"], "geroolyhuicy@gmail.com")
            smtp_inst = mock_smtp.return_value.__enter__.return_value
            smtp_inst.starttls.assert_called_once()
            smtp_inst.login.assert_called_once_with("sender@gmail.com", "app-password-demo")
            smtp_inst.send_message.assert_called_once()
            sent_msg = smtp_inst.send_message.call_args[0][0]
            self.assertEqual(sent_msg["To"], "geroolyhuicy@gmail.com")
            self.assertEqual(sent_msg["Reply-To"], "anhminh@company.vn")
            self.assertNotIn("\n", sent_msg["Subject"])

    def test_tidb_dialect_translation_and_row_compat(self):
        from datetime import date, datetime
        from decimal import Decimal
        from backend.database.connection import _normalize_row, _qmark_to_pyformat, get_db_dialect

        # Test ? -> %s outside literals + literal % escaping when params provided
        sql = "SELECT * FROM orders WHERE note = '100%?' AND code LIKE ? AND id = ?"
        self.assertEqual(
            _qmark_to_pyformat(sql, has_params=True),
            "SELECT * FROM orders WHERE note = '100%%?' AND code LIKE %s AND id = %s",
        )
        self.assertEqual(_qmark_to_pyformat("SELECT * FROM users WHERE email = '?'", has_params=False), "SELECT * FROM users WHERE email = '?'")

        # Test CompatRow both dict & positional indexing + Decimal/date normalization
        row = _normalize_row({"id": 7, "amt": Decimal("125.50"), "dt": date(2026, 11, 11), "ts": datetime(2026, 11, 11, 2, 30, 0)})
        self.assertEqual(row["id"], 7)
        self.assertEqual(row[0], 7)
        self.assertEqual(row["amt"], 125.5)
        self.assertIsInstance(row["amt"], float)
        self.assertEqual(row["dt"], "2026-11-11")
        self.assertEqual(row["ts"], "2026-11-11 02:30:00")

        # With ECOLOGIX_DB_PATH absent and TIDB_HOST set, dialect selects mysql
        with patch.dict(os.environ, {"ECOLOGIX_DB_PATH": "", "TIDB_HOST": "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"}):
            self.assertEqual(get_db_dialect(), "mysql")
