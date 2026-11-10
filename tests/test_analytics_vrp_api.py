"""Tests for LightGBM Forecasting + CSV import, CVRPTW Routing, 6 AI Agents, Contact Email, Exporters & Live SPA."""
import os
from unittest.mock import patch

from backend.services.ai_service import clear_conversation, get_conversation_messages, process_agent_query
from backend.services.email_service import get_contact_recipient, send_contact_email
from backend.services.forecasting_service import get_forecast_for_product, import_sales_history_csv
from backend.services.routing_service import get_pending_orders, optimize_100_points, optimize_routes_for_orders
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
        res = optimize_routes_for_orders(order_ids, vehicle_id=1, enforce_time_window=True, save_to_db=False)
        self.assertIsNotNone(res)
        self.assertGreater(res["total_distance_km"], 0)
        self.assertEqual(len(res["ordered_stops"]), len(order_ids))

        pts50 = optimize_100_points(scope_count=50, enforce_avoidance=True)
        self.assertEqual(pts50["total_points"], 50)
        self.assertEqual(set(pts50["routes"].keys()), {"XE-01", "XE-02", "XE-03"})

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
