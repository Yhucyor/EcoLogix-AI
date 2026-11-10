"""Tests for Authentication lifecycle, HMAC Bearer tokens, OTP, Password Reset & RBAC."""
from backend import config
from tests.support import LiveApiTestCase, http_json


class TestAuthAndRbac(LiveApiTestCase):
    def test_register_verify_login_me_reset_and_rbac(self):
        # 1. Register new Auditor user
        reg_status, reg_body = http_json(
            self.base_url,
            "POST",
            "/api/auth/register",
            {
                "name": "Kiểm Toán Viên Test",
                "email": "auditor.test@ecologix.vn",
                "password": "Password#123",
                "phone": "0909111222",
                "role": "Auditor",
                "company_name": "EcoTest JSC",
            },
        )
        self.assertEqual(reg_status, 200)
        self.assertTrue(reg_body["ok"])
        first_otp = reg_body["demo_otp"]
        self.assertEqual(len(first_otp), 6)

        # Duplicate email rejected
        dup_status, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/register",
            {
                "name": "Dup",
                "email": "auditor.test@ecologix.vn",
                "password": "Password#123",
                "role": "Auditor",
            },
        )
        self.assertEqual(dup_status, 400)

        # Unverified login blocked with 401
        unver_status, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "auditor.test@ecologix.vn", "password": "Password#123"},
        )
        self.assertEqual(unver_status, 401)

        # 2. Resend OTP + Verify wrong then valid OTP
        resend_status, resend_body = http_json(
            self.base_url, "POST", "/api/auth/resend-otp", {"email": "auditor.test@ecologix.vn"}
        )
        self.assertEqual(resend_status, 200)
        new_otp = resend_body["demo_otp"]

        bad_ver_status, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/verify",
            {"email": "auditor.test@ecologix.vn", "otp_code": "000000"},
        )
        self.assertEqual(bad_ver_status, 400)

        ver_status, ver_body = http_json(
            self.base_url,
            "POST",
            "/api/auth/verify",
            {"email": "auditor.test@ecologix.vn", "otp_code": new_otp},
        )
        self.assertEqual(ver_status, 200)
        self.assertTrue(ver_body["ok"])

        # 3. Login + /api/auth/me + invalid token check
        login_status, login_body = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "auditor.test@ecologix.vn", "password": "Password#123"},
        )
        self.assertEqual(login_status, 200)
        auditor_token = login_body["access_token"]
        self.assertTrue(len(auditor_token) > 20)
        self.assertEqual(login_body["user"]["role"], "Auditor")
        self.assertEqual(login_body["user"]["company_name"], "EcoTest JSC")

        me_status, me_body = http_json(self.base_url, "GET", "/api/auth/me", token=auditor_token)
        self.assertEqual(me_status, 200)
        self.assertEqual(me_body["user"]["email"], "auditor.test@ecologix.vn")

        bad_tok_status, _ = http_json(self.base_url, "GET", "/api/auth/me", token="tampered.invalid.sig")
        self.assertEqual(bad_tok_status, 401)

        # 4. RBAC Enforcement: Auditor cannot modify company settings or delete SKU -> 403
        rbac_comp_status, _ = http_json(
            self.base_url,
            "PUT",
            "/api/settings/company",
            {"name": "Blocked Change"},
            token=auditor_token,
        )
        self.assertEqual(rbac_comp_status, 403)

        rbac_del_status, _ = http_json(
            self.base_url, "DELETE", "/api/inventory/products/1", token=auditor_token
        )
        self.assertEqual(rbac_del_status, 403)

        # 5. Strict Auth toggle enforcement
        prev_strict = config.STRICT_AUTH
        try:
            config.STRICT_AUTH = True
            unauth_dash, _ = http_json(self.base_url, "GET", "/api/dashboard")
            self.assertEqual(unauth_dash, 401)
            auth_dash, dash_body = http_json(self.base_url, "GET", "/api/dashboard", token=auditor_token)
            self.assertEqual(auth_dash, 200)
            self.assertIn("financial", dash_body)
            self.assertIn("esg", dash_body)
        finally:
            config.STRICT_AUTH = prev_strict

        # 6. Seeded Manager login succeeds & can update profile + logout
        mgr_status, mgr_body = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "nguyen.van.a@ecologix.vn", "password": "password123"},
        )
        self.assertEqual(mgr_status, 200)
        mgr_token = mgr_body["access_token"]
        self.assertEqual(mgr_body["user"]["role"], "Manager")

        prof_status, prof_body = http_json(
            self.base_url,
            "PUT",
            "/api/settings/profile",
            {"name": "Nguyễn Văn A Updated", "phone": "0901234567"},
            token=mgr_token,
        )
        self.assertEqual(prof_status, 200)
        self.assertTrue(prof_body["ok"])

        out_status, _ = http_json(self.base_url, "POST", "/api/auth/logout", token=mgr_token)
        self.assertEqual(out_status, 200)

        # 7. Forgot + Reset Password flow
        fg_status, fg_body = http_json(
            self.base_url, "POST", "/api/auth/forgot", {"email": "auditor.test@ecologix.vn"}
        )
        self.assertEqual(fg_status, 200)
        reset_status, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/reset",
            {
                "email": "auditor.test@ecologix.vn",
                "token": fg_body["demo_token"],
                "new_password": "NewPassword#999",
            },
        )
        self.assertEqual(reset_status, 200)

        relogin_status, _ = http_json(
            self.base_url,
            "POST",
            "/api/auth/login",
            {"email": "auditor.test@ecologix.vn", "password": "NewPassword#999"},
        )
        self.assertEqual(relogin_status, 200)
