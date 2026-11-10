"""Tests for Inventory CRUD, Stock Transactions, Vehicles, Partners & Orders."""
from backend.database.connection import execute_query
from backend.services.inventory_service import (
    add_product,
    add_warehouse,
    delete_product,
    record_transaction,
    transfer_stock,
    update_product,
)
from backend.services.order_service import create_order, delete_order, get_order_detail, update_order_status
from backend.services.partner_service import add_customer, add_supplier, update_customer, update_supplier
from backend.services.vehicle_service import add_vehicle, delete_vehicle, update_vehicle
from tests.support import IsolatedDbTestCase


class TestInventoryOrdersAndMasterData(IsolatedDbTestCase):
    def test_inventory_product_warehouse_and_tx_lifecycle(self):
        ok, _ = add_warehouse("Kho Test Q7", "WH-TEST-07", "Quận 7, TP.HCM", 1800.0)
        self.assertTrue(ok)

        ok, _ = add_product(1, "SKU-TEST-99", "Trà Oolong Hữu Cơ", "Đồ uống", "Thùng", 165000.0, 8.5, 30, 250)
        self.assertTrue(ok)
        row = execute_query("SELECT id FROM products WHERE sku = 'SKU-TEST-99';")[0]
        pid = row["id"]

        ok, _ = update_product(pid, "Trà Oolong Matcha", "Đồ uống", "Thùng", 175000.0, 9.0, 40, 300)
        self.assertTrue(ok)

        # IN transaction increases stock
        ok, _ = record_transaction(pid, 1, "IN", 50, note="Test inbound")
        self.assertTrue(ok)
        qty_after_in = execute_query("SELECT quantity FROM inventory WHERE product_id = ? AND warehouse_id = 1;", (pid,))[0]["quantity"]
        self.assertEqual(qty_after_in, 80)  # min_stock(30) + 50

        # Non-negative stock guard on OUT
        ok_over, msg_over = record_transaction(pid, 1, "OUT", 999999, note="Excessive out")
        self.assertFalse(ok_over)
        self.assertIn("Tồn kho không đủ", msg_over)

        # Transfer between warehouses
        wh_test = execute_query("SELECT id FROM warehouses WHERE code = 'WH-TEST-07';")[0]["id"]
        ok_tr, _ = transfer_stock(pid, 1, wh_test, 20, note="Transfer test")
        self.assertTrue(ok_tr)

        # Deleting product removes fresh test SKU cleanly
        ok_del, _ = delete_product(pid)
        self.assertTrue(ok_del)

    def test_order_creation_stock_deduction_and_delete(self):
        before_qty = execute_query("SELECT quantity FROM inventory WHERE product_id = 1 AND warehouse_id = 1;")[0]["quantity"]
        ok, msg, oid = create_order(
            order_code="ORD-TEST-2026",
            customer_id=1,
            warehouse_id=1,
            time_window_start="09:00",
            time_window_end="11:00",
            items=[{"product_id": 1, "quantity": 5}],
            shipping_fee=210000.0,
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(oid)

        detail = get_order_detail(oid)
        self.assertEqual(detail["order_code"], "ORD-TEST-2026")
        self.assertEqual(detail["time_window_start"], "09:00")
        self.assertEqual(len(detail["items"]), 1)

        after_qty = execute_query("SELECT quantity FROM inventory WHERE product_id = 1 AND warehouse_id = 1;")[0]["quantity"]
        self.assertEqual(after_qty, max(0, before_qty - 5))

        ok_st, _ = update_order_status(oid, "PROCESSING")
        self.assertTrue(ok_st)
        ok_del, _ = delete_order(oid)
        self.assertTrue(ok_del)

    def test_vehicles_and_partners_crud(self):
        ok, _ = add_vehicle("51D-777.99", "Xe Điện Test EV", "Tải nhẹ đô thị", 1800, "Electric", 0.0, 2900.0)
        self.assertTrue(ok)
        vid = execute_query("SELECT id FROM vehicles WHERE plate_number = '51D-777.99';")[0]["id"]
        ok_u, _ = update_vehicle(vid, "Xe Điện Test EV v2", "Tải van xanh", 2000, "Electric", 0.0, 2700.0, "Available")
        self.assertTrue(ok_u)
        ok_d, _ = delete_vehicle(vid)
        self.assertTrue(ok_d)

        ok_c, _ = add_customer("Đại lý Test Xanh", "0908333444", "dl@test.vn", "12 Nguyễn Văn Cừ", "Quận 1", "TP.HCM", "VIP")
        self.assertTrue(ok_c)
        cid = execute_query("SELECT id FROM customers WHERE name = 'Đại lý Test Xanh';")[0]["id"]
        self.assertTrue(update_customer(cid, "Đại lý Test Xanh Updated", "0908333444", "dl@test.vn", "12 Nguyễn Văn Cừ", "Quận 1", "TP.HCM", "Enterprise")[0])

        ok_s, _ = add_supplier("NCC Test Bao Bì", "02839998888", "ncc@test.vn", "KCN Sóng Thần", "Thùng Carton", 1500000.0)
        self.assertTrue(ok_s)
        sid = execute_query("SELECT id FROM suppliers WHERE name = 'NCC Test Bao Bì';")[0]["id"]
        self.assertTrue(update_supplier(sid, "NCC Test Bao Bì Updated", "02839998888", "ncc@test.vn", "Dĩ An", "Thùng Carton Eco", 800000.0)[0])

