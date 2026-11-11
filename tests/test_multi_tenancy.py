"""
Tests for EcoLogix AI multi-tenant data isolation.
Verifies that accounts from different companies are completely scoped to their own data
and cannot view, mutate, or optimize each other's warehouses, products, orders, vehicles, routes, or settings.
"""
import unittest
from tests.support import LiveApiTestCase, http_json


class TestMultiTenancyIsolation(LiveApiTestCase):

    def test_multi_tenant_data_isolation(self):
        # 1. Login as Admin of Company 1
        st1, body1 = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "admin@ecologix.vn", "password": "password123"},
        )
        self.assertEqual(st1, 200)
        tok1 = body1["access_token"]
        comp1_id = body1["user"]["company_id"]
        self.assertEqual(comp1_id, 1)

        # 2. Register a new user for Company 2
        st_reg, body_reg = http_json(
            self.base_url,
            "POST",
            "/api/auth/register",
            {
                "name": "Trần Thị B",
                "email": "tran.thi.b@company2.vn",
                "password": "Password#2026",
                "role": "Manager",
                "company_name": "Công Ty Cổ Phần Logistics Miền Tây",
            },
        )
        self.assertEqual(st_reg, 200)
        otp2 = body_reg.get("demo_otp")

        # Verify account for Company 2
        st_v, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/verify",
            {"email": "tran.thi.b@company2.vn", "otp_code": otp2},
        )
        self.assertEqual(st_v, 200)

        # Login as Company 2 Manager
        st2, body2 = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "tran.thi.b@company2.vn", "password": "Password#2026"},
        )
        self.assertEqual(st2, 200)
        tok2 = body2["access_token"]
        comp2_id = body2["user"]["company_id"]
        self.assertNotEqual(comp1_id, comp2_id)
        self.assertEqual(body2["user"]["company_name"], "Công Ty Cổ Phần Logistics Miền Tây")

        # 3. Check Orders isolation
        st_ord1, body_ord1 = http_json(self.base_url, "GET", "/api/orders", token=tok1)
        self.assertEqual(st_ord1, 200)
        orders1_codes = {o["order_code"] for o in body_ord1["orders"]}

        st_ord2, body_ord2 = http_json(self.base_url, "GET", "/api/orders", token=tok2)
        self.assertEqual(st_ord2, 200)
        orders2_codes = {o["order_code"] for o in body_ord2["orders"]}

        # Company 1 and Company 2 must not see each other's orders
        self.assertTrue(len(orders1_codes.intersection(orders2_codes)) == 0)

        # 4. Check Vehicles isolation
        st_v1, body_v1 = http_json(self.base_url, "GET", "/api/vehicles", token=tok1)
        self.assertEqual(st_v1, 200)
        veh1_plates = {v["plate_number"] for v in body_v1["vehicles"]}

        st_v2, body_v2 = http_json(self.base_url, "GET", "/api/vehicles", token=tok2)
        self.assertEqual(st_v2, 200)
        veh2_plates = {v["plate_number"] for v in body_v2["vehicles"]}

        self.assertTrue(len(veh1_plates.intersection(veh2_plates)) == 0)

        # 5. Check Inventory Warehouses & Products isolation
        st_inv1, body_inv1 = http_json(self.base_url, "GET", "/api/inventory", token=tok1)
        self.assertEqual(st_inv1, 200)
        wh1_codes = {w["code"] for w in body_inv1["warehouses"]}

        st_inv2, body_inv2 = http_json(self.base_url, "GET", "/api/inventory", token=tok2)
        self.assertEqual(st_inv2, 200)
        wh2_codes = {w["code"] for w in body_inv2["warehouses"]}

        self.assertTrue(len(wh1_codes.intersection(wh2_codes)) == 0)

        # 6. Check Settings RBAC Team isolation
        st_set1, body_set1 = http_json(self.base_url, "GET", "/api/settings", token=tok1)
        self.assertEqual(st_set1, 200)
        users1_emails = {u["email"] for u in body_set1["users"]}
        self.assertIn("admin@ecologix.vn", users1_emails)
        self.assertNotIn("tran.thi.b@company2.vn", users1_emails)

        st_set2, body_set2 = http_json(self.base_url, "GET", "/api/settings", token=tok2)
        self.assertEqual(st_set2, 200)
        users2_emails = {u["email"] for u in body_set2["users"]}
        self.assertIn("tran.thi.b@company2.vn", users2_emails)
        self.assertNotIn("admin@ecologix.vn", users2_emails)

        # 7. Check Cross-Company Tampering is forbidden / isolated
        # Company 2 user tries to delete an order belonging to Company 1
        comp1_order_id = body_ord1["orders"][0]["id"]
        st_del, body_del = http_json(self.base_url, "DELETE", f"/api/orders/{comp1_order_id}", token=tok2)
        self.assertEqual(st_del, 400)  # Cannot find / delete order of another company

        # Company 2 user tries to delete a vehicle belonging to Company 1
        comp1_veh_id = body_v1["vehicles"][0]["id"]
        st_del_v, body_del_v = http_json(self.base_url, "DELETE", f"/api/vehicles/{comp1_veh_id}", token=tok2)
        self.assertEqual(st_del_v, 400)  # Cannot find / delete vehicle of another company

        # 8. Check Partners isolation (Customers & Suppliers)
        st_p1, body_p1 = http_json(self.base_url, "GET", "/api/partners", token=tok1)
        self.assertEqual(st_p1, 200)
        cust1_names = {c["name"] for c in body_p1["customers"]}

        st_p2, body_p2 = http_json(self.base_url, "GET", "/api/partners", token=tok2)
        self.assertEqual(st_p2, 200)
        cust2_names = {c["name"] for c in body_p2["customers"]}

        self.assertTrue(len(cust1_names.intersection(cust2_names)) == 0)

        # 9. Check Routing Init isolation
        st_r1, body_r1 = http_json(self.base_url, "GET", "/api/routing", token=tok1)
        self.assertEqual(st_r1, 200)
        self.assertTrue(all(v["id"] in [x["id"] for x in body_v1["vehicles"]] for v in body_r1["vehicles"]))

        st_r2, body_r2 = http_json(self.base_url, "GET", "/api/routing", token=tok2)
        self.assertEqual(st_r2, 200)
        self.assertTrue(all(v["id"] in [x["id"] for x in body_v2["vehicles"]] for v in body_r2["vehicles"]))

        # 10. Check Dashboard isolation
        st_d1, body_d1 = http_json(self.base_url, "GET", "/api/dashboard", token=tok1)
        self.assertEqual(st_d1, 200)
        st_d2, body_d2 = http_json(self.base_url, "GET", "/api/dashboard", token=tok2)
        self.assertEqual(st_d2, 200)
        self.assertNotEqual(body_d1["company_name"], body_d2["company_name"])
        self.assertEqual(body_d2["company_name"], "Công Ty Cổ Phần Logistics Miền Tây")


if __name__ == "__main__":
    unittest.main()
