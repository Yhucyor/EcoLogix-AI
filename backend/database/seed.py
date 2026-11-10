"""
EcoLogix AI - Complete 24-Table Database Seeder
Nạp dữ liệu mẫu thực tế, liên kết chặt chẽ cho TP.HCM, Bình Dương và Đồng Nai.
Đảm bảo tất cả 24 bảng nghiệp vụ đều có dữ liệu liên kết thực tế.
"""
import json
import random
from datetime import datetime, timedelta
from backend.database.connection import get_db
from backend.database.models import init_database
from backend.utils.helpers import hash_password


def seed_all():
    init_database()
    random.seed(2026)

    with get_db() as conn:
        cursor = conn.cursor()

        tables_clear_order = [
            "activity_logs", "notifications", "system_settings", "esg_reports",
            "carbon_emissions", "expenses", "ai_messages", "ai_conversations",
            "ai_agents", "forecasts", "route_stops", "routes", "order_items",
            "orders", "vehicles", "suppliers", "customers",
            "inventory_transactions", "inventory", "products", "warehouses",
            "users", "roles", "companies",
        ]
        for t in tables_clear_order:
            cursor.execute(f"DELETE FROM {t};")
        cursor.execute("DELETE FROM sqlite_sequence;")

        # 1. ROLES (RBAC)
        roles = [
            ("Admin", "Quản trị viên toàn hệ thống", "ALL"),
            ("Manager", "Giám đốc vận hành & Logistics", "READ,WRITE,OPTIMIZE,EXPORT,SETTINGS"),
            ("Dispatcher", "Điều phối viên đội xe & đơn hàng", "READ,WRITE_ORDERS,DISPATCH,OPTIMIZE"),
            ("Auditor", "Kiểm toán viên ESG & Tài chính", "READ,EXPORT_ESG,FINANCIAL"),
        ]
        cursor.executemany("INSERT INTO roles (name, description, permissions) VALUES (?, ?, ?);", roles)

        # 2. COMPANIES
        cursor.execute("""
        INSERT INTO companies (name, tax_code, industry, size, address, city, phone, email)
        VALUES (
            'Công Ty TNHH Phân Phối & Logistics Xanh EcoLogix',
            '0317892345',
            'Phân phối Hàng tiêu dùng (FMCG) & Logistics',
            'SMEs (50-100 nhân sự)',
            'Khu Công Nghệ Cao, P. Tăng Nhơn Phú B, TP. Thủ Đức',
            'TP. Hồ Chí Minh',
            '028 3896 5555',
            'contact@ecologix.vn'
        );
        """)
        company_id = cursor.lastrowid

        # 3. USERS (Mật khẩu băm PBKDF2-SHA256)
        demo_pw_hash = hash_password("password123")
        users = [
            (company_id, "Nguyễn Văn A", "nguyen.van.a@ecologix.vn", demo_pw_hash, "Manager",
             "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150", "0908123456", 1),
            (company_id, "Nguyễn Thị Thùy", "thuy.nguyen@abc.com", demo_pw_hash, "Dispatcher",
             "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150", "0912456789", 1),
            (company_id, "Trần Minh Tuấn", "tuan.tran@ecologix.vn", demo_pw_hash, "Auditor",
             "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150", "0933789012", 1),
            (company_id, "Quản trị Hệ thống", "admin@ecologix.vn", demo_pw_hash, "Admin",
             "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150", "02888886688", 1),
        ]
        cursor.executemany("""
        INSERT INTO users (company_id, name, email, password_hash, role, avatar_url, phone, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, users)
        cursor.execute("SELECT id FROM users ORDER BY id ASC;")
        user_ids = [r[0] for r in cursor.fetchall()]

        # 4. WAREHOUSES
        warehouses = [
            (company_id, "Kho Tổng EcoLogix Thủ Đức Hub", "WH-HCM-01", "Khu Công Nghệ Cao, TP. Thủ Đức, TP.HCM", 10.8505, 106.7718, 5000.0, 78.5, 1),
            (company_id, "Kho Trung Chuyển Dĩ An (Bình Dương)", "WH-BD-02", "KCN Sóng Thần 1, Dĩ An, Bình Dương", 10.9067, 106.7725, 3200.0, 64.0, 0),
            (company_id, "Kho Vệ Tinh Amata (Đồng Nai)", "WH-DN-03", "KCN Amata, TP. Biên Hòa, Đồng Nai", 10.9423, 106.8833, 3800.0, 71.2, 0),
        ]
        cursor.executemany("""
        INSERT INTO warehouses (company_id, name, code, address, lat, lng, capacity_m3, current_utilization_pct, is_central_hub)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, warehouses)

        # 5. PRODUCTS
        products = [
            (company_id, "SKU-001", "Nước Ngọt Giải Khát Lon 330ml (Thùng 24)", "Đồ uống", "Thùng", 210000, 8.5, 90, 450),
            (company_id, "SKU-002", "Dầu Ăn Thực Vật Cao Cấp 1L (Thùng 12)", "Thực phẩm", "Thùng", 420000, 11.2, 40, 300),
            (company_id, "SKU-003", "Mì Gói Hảo Vị Tôm Chua Cay (Thùng 30)", "Thực phẩm khô", "Thùng", 115000, 2.8, 80, 600),
            (company_id, "SKU-004", "Bột Giặt Sinh Học EcoClean 3kg (Bao)", "Hóa mỹ phẩm", "Bao", 165000, 3.1, 30, 250),
            (company_id, "SKU-005", "Sữa Tươi Tiệt Trùng 1L (Thùng 12)", "Sữa & Chế phẩm", "Thùng", 360000, 12.5, 60, 450),
            (company_id, "SKU-006", "Gạo ST25 Hữu Cơ Thượng Hạng (Bao 5kg)", "Lương thực", "Bao", 195000, 5.0, 50, 350),
        ]
        cursor.executemany("""
        INSERT INTO products (company_id, sku, name, category, unit, unit_price, weight_kg, min_stock, max_stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, products)

        cursor.execute("SELECT id FROM warehouses;")
        wh_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT id, unit_price, weight_kg FROM products;")
        prod_rows = cursor.fetchall()
        prod_ids = [r[0] for r in prod_rows]

        # 6. INVENTORY
        # Lưu ý: SKU-001 ở Kho Tổng có quantity thấp hơn safety_stock để kích hoạt cảnh báo thật
        quantities = {
            wh_ids[0]: [75, 180, 450, 120, 310, 260],
            wh_ids[1]: [120, 85, 210, 60, 140, 110],
            wh_ids[2]: [150, 95, 280, 75, 160, 130],
        }
        inventory_rows = []
        for wh_id in wh_ids:
            wh_q = quantities.get(wh_id, [100] * len(prod_ids))
            for i, p_id in enumerate(prod_ids):
                qty = wh_q[i]
                safety = 95 if i == 0 and wh_id == wh_ids[0] else int(qty * 0.4)
                reorder = int(safety * 1.6)
                inventory_rows.append((wh_id, p_id, qty, safety, reorder))
        cursor.executemany("""
        INSERT INTO inventory (warehouse_id, product_id, quantity, safety_stock, reorder_point)
        VALUES (?, ?, ?, ?, ?);
        """, inventory_rows)

        # 7. INVENTORY TRANSACTIONS
        now = datetime(2026, 11, 10, 14, 0, 0)
        inv_txs = [
            (prod_ids[0], wh_ids[0], "IN", 200, "PO-2026-101", "Nhập hàng đầu tuần từ NCC Tân Bình", (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")),
            (prod_ids[0], wh_ids[0], "OUT", 125, "ORD-2026-001", "Xuất giao đại lý Quận 1 & Quận 3", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
            (prod_ids[1], wh_ids[1], "TRANSFER", 40, "TRF-2026-014", "Điều chuyển bổ sung sang kho Dĩ An", (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
            (prod_ids[2], wh_ids[2], "IN", 180, "PO-2026-104", "Nhập bổ sung Mì gói cho cụm Đồng Nai", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
            (prod_ids[3], wh_ids[0], "ADJUST", 5, "ADJ-2026-002", "Kiểm kê định kỳ tháng 11/2026", (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
        ]
        cursor.executemany("""
        INSERT INTO inventory_transactions (product_id, warehouse_id, transaction_type, quantity, reference_code, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, inv_txs)

        # 8. VEHICLES
        vehicles = [
            (company_id, "51C-892.45", "Xe Tải Eco 1.5T #01", "Tải nhẹ Thaco Towner", 1500.0, "Diesel", 11.5, 3800.0, "Available"),
            (company_id, "60B-341.12", "Xe Tải Eco 2.5T #02", "Tải trung Isuzu Forward", 2500.0, "Diesel", 14.0, 4500.0, "Available"),
            (company_id, "61C-772.89", "Xe Tải Eco 5 Tấn #03", "Xe Tải 5 Tấn Hino 500", 5000.0, "Diesel", 18.5, 5800.0, "In Transit"),
            (company_id, "50E-128.90", "Xe Điện Eco Electric 1.2T #04", "EV Van GreenSpeed (Net-Zero)", 1200.0, "Electric", 0.0, 2600.0, "Available"),
        ]
        cursor.executemany("""
        INSERT INTO vehicles (company_id, plate_number, vehicle_name, vehicle_type, max_load_kg, fuel_type, fuel_consumption_per_100km, operational_cost_per_km, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, vehicles)
        cursor.execute("SELECT id FROM vehicles ORDER BY id ASC;")
        veh_ids = [r[0] for r in cursor.fetchall()]

        # 9. CUSTOMERS
        customers = [
            (company_id, "Đại Lý Bách Hóa Minh Khang", "0903112233", "minhkhang@gmail.com", "125 Lê Lợi, P. Bến Nghé", "Quận 1", "TP.HCM", 10.7769, 106.7009, "VIP", 45000000),
            (company_id, "Siêu Thị Mini Tiện Lợi Q3", "0903223344", "tienloiq3@gmail.com", "48 Võ Văn Tần, P. Võ Thị Sáu", "Quận 3", "TP.HCM", 10.7828, 106.6872, "Standard", 28000000),
            (company_id, "Chuỗi Tạp Hóa Chợ Lớn Q5", "0903334455", "cholon5@gmail.com", "210 Hải Thượng Lãn Ông, P. 13", "Quận 5", "TP.HCM", 10.7554, 106.6669, "VIP", 62000000),
            (company_id, "Đại Lý Phân Phối Sư Vạn Hạnh", "0903445566", "svh10@gmail.com", "382 Sư Vạn Hạnh, P. 12", "Quận 10", "TP.HCM", 10.7725, 106.6672, "Standard", 19500000),
            (company_id, "Cửa Hàng Xanh Thảo Điền", "0903556677", "thaodien@gmail.com", "12 Quốc Hương, P. Thảo Điền", "TP. Thủ Đức", "TP.HCM", 10.8062, 106.7351, "VIP", 54000000),
            (company_id, "Bách Hóa Tân Lập Dĩ An", "0903667788", "tanlap@gmail.com", "89 Nguyễn Tri Phương, An Bình", "Dĩ An", "Bình Dương", 10.9022, 106.7584, "Standard", 31000000),
            (company_id, "Kho Bán Buôn Thủ Dầu Một", "0903778899", "tdm@gmail.com", "45 Đại Lộ Bình Dương, Phú Hòa", "Thủ Dầu Một", "Bình Dương", 10.9804, 106.6746, "VIP", 78000000),
            (company_id, "Đại Lý Tiện Ích Thuận An", "0903889900", "thuanan@gmail.com", "12 ĐT743, An Phú", "Thuận An", "Bình Dương", 10.9333, 106.7167, "Standard", 24000000),
            (company_id, "Tổng Đại Lý Biên Hòa Tân Mai", "0903990011", "tanmai@gmail.com", "15 Đồng Khởi, P. Tân Mai", "Biên Hòa", "Đồng Nai", 10.9574, 106.8427, "VIP", 85000000),
            (company_id, "Cửa Hàng Hàng Tiêu Dùng Long Thành", "0903001122", "longthanh@gmail.com", "78 Lê Duẩn, TT. Long Thành", "Long Thành", "Đồng Nai", 10.7932, 106.9538, "Standard", 33000000),
        ]
        cursor.executemany("""
        INSERT INTO customers (company_id, name, phone, email, address, district, province, lat, lng, customer_tier, total_spent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, customers)
        cursor.execute("SELECT id, district, province, lat, lng, address FROM customers ORDER BY id ASC;")
        cust_rows = cursor.fetchall()

        # 10. SUPPLIERS
        suppliers = [
            (company_id, "Công Ty CP Nước Giải Khát & Đồ Uống Tân Bình", "028 3811 2233", "supply@tanbinhbev.vn", "KCN Tân Bình, TP.HCM", "Nước ngọt lon, Nước khoáng", 15000000),
            (company_id, "Tập Đoàn Dầu Thực Vật Miền Nam", "028 3822 4455", "sales@southoil.vn", "KCN Hiệp Phước, Nhà Bè, TP.HCM", "Dầu ăn thực vật 1L", 28000000),
            (company_id, "Tổng Công Ty Lương Thực Sài Gòn", "028 3833 6677", "contact@saigonfood.vn", "Bình Tân, TP.HCM", "Gạo ST25, Mì gói", 8500000),
        ]
        cursor.executemany("""
        INSERT INTO suppliers (company_id, name, phone, email, address, products_supplied, debt_vnd)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, suppliers)

        # 11 & 12. ORDERS (28 đơn) + ORDER ITEMS (dữ liệu liên kết đầy đủ)
        base_orders = [
            ("ORD-2026-001", 0, 0, "COMPLETED", "08:00", "11:30", 1, 25),
            ("ORD-2026-002", 1, 0, "COMPLETED", "09:00", "12:00", 1, 22),
            ("ORD-2026-003", 2, 0, "SHIPPING", "13:30", "16:00", 1, 18),
            ("ORD-2026-004", 3, 0, "SHIPPING", "14:00", "16:00", 1, 15),
            ("ORD-2026-005", 4, 0, "PROCESSING", "10:00", "14:00", 0, 12),
            ("ORD-2026-006", 5, 1, "PROCESSING", "08:30", "11:30", 0, 10),
            ("ORD-2026-007", 6, 1, "PENDING", "18:30", "21:00", 0, 4),
            ("ORD-2026-008", 7, 1, "PENDING", "18:30", "21:00", 0, 3),
            ("ORD-2026-009", 8, 2, "SHIPPING", "08:00", "12:00", 0, 2),
            ("ORD-2026-010", 9, 2, "PENDING", "13:00", "17:00", 0, 1),
        ]
        for idx in range(11, 29):
            c_idx = (idx - 1) % len(cust_rows)
            w_idx = idx % len(wh_ids)
            st_choice = ["PENDING", "PROCESSING", "SHIPPING", "COMPLETED"][idx % 4]
            restr = 1 if cust_rows[c_idx][1] in ("Quận 1", "Quận 3", "Quận 5", "Quận 10") else 0
            tw_s, tw_e = ("18:30", "21:00") if restr and idx % 2 == 0 else ("08:00", "15:30")
            days_ago = max(0, 30 - idx)
            base_orders.append((f"ORD-2026-{idx:03d}", c_idx, w_idx, st_choice, tw_s, tw_e, restr, days_ago))

        order_ids = []
        order_items_batch = []
        for code, c_idx, w_idx, status, tw_s, tw_e, restr, days_ago in base_orders:
            selected_prods = random.sample(prod_rows, k=2)
            total_w = 0.0
            total_amt = 0.0
            line_items = []
            for p_id, u_price, u_weight in selected_prods:
                qty = random.randint(6, 22)
                total_w += qty * u_weight
                total_amt += qty * u_price
                line_items.append((p_id, qty, u_price))
            fee = 140000 + int(total_w * 550)
            created_str = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO orders (company_id, order_code, customer_id, warehouse_id, status, total_weight_kg, total_amount, shipping_fee, time_window_start, time_window_end, is_urban_restricted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (company_id, code, cust_rows[c_idx][0], wh_ids[w_idx], status, round(total_w, 1), round(total_amt, 0), fee, tw_s, tw_e, restr, created_str))
            o_id = cursor.lastrowid
            order_ids.append((o_id, c_idx))
            for p_id, qty, u_price in line_items:
                order_items_batch.append((o_id, p_id, qty, u_price))

        cursor.executemany("""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?);
        """, order_items_batch)

        # 13 & 14 & 20. ROUTES, ROUTE STOPS & CARBON EMISSIONS
        route_specs = [
            ("RT-2026-1101", veh_ids[0], "2026-11-10", "Optimized", 42.8, 52.2, 1.85, 4.92, 1.08, 13.19, 2.89, 325000, [0, 1, 2, 3]),
            ("RT-2026-1102", veh_ids[2], "2026-11-10", "In Transit", 68.5, 83.6, 2.40, 12.67, 2.79, 33.96, 7.48, 720000, [5, 6, 7]),
            ("RT-2026-1103", veh_ids[3], "2026-11-09", "Completed", 36.4, 44.5, 1.35, 0.0, 4.20, 0.0, 11.25, 125000, [4, 8, 9]),
        ]
        for r_code, v_id, r_date, r_stat, dist, b_dist, hrs, fuel, f_saved, co2, c_saved, cost, ord_idxs in route_specs:
            cursor.execute("""
            INSERT INTO routes (route_code, vehicle_id, route_date, status, total_distance_km, baseline_distance_km, saved_distance_km,
                                total_time_hours, fuel_consumed_liters, fuel_saved_liters, co2_emission_kg, saved_co2_kg, total_cost_vnd, saved_cost_vnd, is_optimized)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """, (r_code, v_id, r_date, r_stat, dist, b_dist, round(b_dist - dist, 1), hrs, fuel, f_saved, co2, c_saved, cost, round(cost * 0.22, 0)))
            r_id = cursor.lastrowid
            for seq, oi in enumerate(ord_idxs, start=1):
                o_id, c_idx = order_ids[oi]
                c_row = cust_rows[c_idx]
                arr_h = 8 + seq
                cursor.execute("""
                INSERT INTO route_stops (route_id, order_id, stop_sequence, arrival_time, departure_time, lat, lng, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (r_id, o_id, seq, f"{arr_h:02d}:15", f"{arr_h:02d}:35", c_row[3], c_row[4], f"{c_row[5]}, {c_row[1]}, {c_row[2]}"))

            cursor.execute("""
            INSERT INTO carbon_emissions (route_id, co2_kg, fuel_liters, calculation_date, standard)
            VALUES (?, ?, ?, ?, 'GHG Protocol Scope 1');
            """, (r_id, co2, fuel, r_date))

        # 15. FORECASTS (Lưu lịch sử dự báo LightGBM mẫu)
        forecast_rows = []
        for idx, p_id in enumerate(prod_ids):
            base_pred = 60 + idx * 14
            for day_offset in range(1, 8):
                f_date = (now + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                pred = base_pred + (15 if day_offset in (5, 6) else 0)
                forecast_rows.append((p_id, f_date, pred, base_pred - 3, max(10, pred - 14), pred + 14, 30, 80 + idx * 10, 145 + idx * 15, 94.6, "LightGBM Regressor"))
        cursor.executemany("""
        INSERT INTO forecasts (product_id, forecast_date, predicted_demand, actual_demand, confidence_lower, confidence_upper, horizon_days, safety_stock, reorder_point, accuracy_pct, model_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, forecast_rows)

        # 16. AI AGENTS
        agents = [
            ("Supervisor Agent", "Điều Phối Cấp Cao", "Tiếp nhận câu lệnh tiếng Việt, phân rã mục tiêu và chỉ định các Agent chuyên trách thực thi.", "EcoLogix-Supervisor-v2"),
            ("Demand Forecasting Agent", "Chuyên Gia Dự Báo Cầu", "Sử dụng LightGBM phân tích chuỗi thời gian bán hàng và biến động mùa vụ.", "LightGBM-Forecast-v2"),
            ("Inventory Management Agent", "Quản Lý Kho Thông Minh", "Giám sát ngưỡng an toàn (Safety Stock), Reorder Point và cảnh báo thiếu hàng.", "EcoLogix-Inventory-v2"),
            ("Route Optimization Agent", "Chuyên Gia Tối Ưu Lộ Trình", "Giải bài toán CVRPTW, né giờ cấm tải nội đô TP.HCM và ưu tiên xe điện EV.", "EcoLogix-CVRPTW-v2"),
            ("Financial Analysis Agent", "Chuyên Viên Phân Tích Tài Chính", "Đo lường chi phí vận hành, tính ROI, giá vốn lưu kho và độ nhạy giá xăng.", "EcoLogix-Finance-v2"),
            ("ESG & Carbon Analysis Agent", "Kiểm Toán Viên Net-Zero & ESG", "Đo lường phát thải CO2 theo GHG Protocol Scope 1 và xuất báo cáo ESG.", "EcoLogix-ESG-v2"),
        ]
        cursor.executemany("INSERT INTO ai_agents (agent_name, role, description, model_name) VALUES (?, ?, ?, ?);", agents)

        # 17 & 18. AI CONVERSATIONS & AI MESSAGES
        cursor.execute("INSERT INTO ai_conversations (user_id, title) VALUES (?, 'Tối ưu tuyến Bình Dương & Kiểm tra ESG tháng 11');", (user_ids[0],))
        conv_id = cursor.lastrowid
        init_trace = json.dumps([
            {"agent": "Supervisor Agent", "action": "Phân loại yêu cầu: Tối ưu chi phí điều xe đi Bình Dương (5 đơn)."},
            {"agent": "Route Optimization Agent", "action": "Tính toán khoảng cách khứ hồi Depot Thủ Đức -> Thuận An -> Dĩ An -> Thủ Dầu Một (68.5 km)."},
            {"agent": "ESG & Carbon Analysis Agent", "action": "Đo lường mức cắt giảm 16.5 kg CO2 so với phương án truyền thống."}
        ], ensure_ascii=False)
        cursor.executemany("""
        INSERT INTO ai_messages (conversation_id, sender, agent_name, content, reasoning_trace)
        VALUES (?, ?, ?, ?, ?);
        """, [
            (conv_id, "user", None, "Tối nay đi 5 đơn Bình Dương dùng xe nào rẻ nhất?", None),
            (conv_id, "assistant", "Supervisor Agent",
             "Tôi đã phân tích dữ liệu đơn hàng Bình Dương và đề xuất sử dụng **Xe Điện Eco Electric 1.2T #04** hoặc **Xe tải 5T #03** để gom chuyến, tiết kiệm **22% chi phí** và cắt giảm **16.5 kg CO₂**.",
             init_trace),
        ])

        # 19. EXPENSES (T7 - T11 / 2026)
        expenses_data = [
            (company_id, "fuel", 42500000, "2026-07-31", "Chi phí xăng dầu tháng 7"),
            (company_id, "labor", 65000000, "2026-07-31", "Lương tài xế & vận hành kho tháng 7"),
            (company_id, "storage", 28000000, "2026-07-31", "Chi phí thuê kho bãi tháng 7"),
            (company_id, "carbon_tax", 2150000, "2026-07-31", "Thuế carbon phát thải tháng 7"),

            (company_id, "fuel", 39800000, "2026-08-31", "Chi phí xăng dầu tháng 8"),
            (company_id, "labor", 65000000, "2026-08-31", "Lương tài xế & vận hành kho tháng 8"),
            (company_id, "storage", 27000000, "2026-08-31", "Chi phí thuê kho bãi tháng 8"),
            (company_id, "carbon_tax", 1980000, "2026-08-31", "Thuế carbon phát thải tháng 8"),

            (company_id, "fuel", 36200000, "2026-09-30", "Chi phí xăng dầu tháng 9"),
            (company_id, "labor", 66000000, "2026-09-30", "Lương tài xế & vận hành kho tháng 9"),
            (company_id, "storage", 24000000, "2026-09-30", "Chi phí thuê kho bãi tháng 9"),
            (company_id, "carbon_tax", 1750000, "2026-09-30", "Thuế carbon phát thải tháng 9"),

            (company_id, "fuel", 33500000, "2026-10-31", "Chi phí xăng dầu tháng 10 (Áp dụng AI VRP)"),
            (company_id, "labor", 66000000, "2026-10-31", "Lương tài xế & vận hành kho tháng 10"),
            (company_id, "storage", 19500000, "2026-10-31", "Chi phí thuê kho bãi tháng 10"),
            (company_id, "carbon_tax", 1450000, "2026-10-31", "Thuế carbon phát thải tháng 10"),

            (company_id, "fuel", 29400000, "2026-11-10", "Chi phí xăng dầu kỳ đầu tháng 11"),
            (company_id, "labor", 64000000, "2026-11-10", "Lương tài xế & vận hành kho tháng 11"),
            (company_id, "storage", 18500000, "2026-11-10", "Chi phí thuê kho bãi tháng 11"),
            (company_id, "carbon_tax", 1180000, "2026-11-10", "Thuế carbon phát thải tháng 11"),
        ]
        cursor.executemany("""
        INSERT INTO expenses (company_id, category, amount_vnd, expense_date, note)
        VALUES (?, ?, ?, ?, ?);
        """, expenses_data)

        # 20. ESG REPORTS (T7 - T11)
        esg_data = [
            (company_id, 7, 2026, 3050.0, 210.0, 84.0, "/api/reports/export/pdf"),
            (company_id, 8, 2026, 2850.0, 310.0, 88.5, "/api/reports/export/pdf"),
            (company_id, 9, 2026, 2620.0, 380.0, 91.2, "/api/reports/export/pdf"),
            (company_id, 10, 2026, 2340.0, 412.0, 94.0, "/api/reports/export/pdf"),
            (company_id, 11, 2026, 2120.0, 465.0, 95.2, "/api/reports/export/pdf"),
        ]
        cursor.executemany("""
        INSERT INTO esg_reports (company_id, month, year, total_co2_kg, co2_saved_kg, green_logistics_score, report_url)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, esg_data)

        # 21. SYSTEM SETTINGS
        settings = [
            (company_id, "FUEL_PRICE_PER_LITER", "23500", "Giá xăng/dầu cơ sở áp dụng (VNĐ/Lít)"),
            (company_id, "CARBON_TAX_RATE", "500", "Đơn giá thuế phát thải Carbon (VNĐ/kg CO2)"),
            (company_id, "MAX_VEHICLE_LOAD_KG", "1500", "Tải trọng xe tối đa tiêu chuẩn (kg)"),
            (company_id, "RESTRICTED_TIME_WINDOW", "16:00-18:00", "Khung giờ cấm xe tải lưu thông nội đô"),
            (company_id, "ESG_TARGET_REDUCTION_PCT", "18.0", "Mục tiêu cắt giảm phát thải CO2 (%)"),
            (company_id, "AI_PROVIDER_MODE", "Hybrid-Demo", "Chế độ Multi-Agent (Hybrid-Demo / Gemini / OpenAI)"),
            (company_id, "LLM_API_KEY", "", "API Key LLM tùy chọn (để trống để chạy chế độ Demo nội bộ)"),
        ]
        cursor.executemany("""
        INSERT INTO system_settings (company_id, setting_key, setting_value, description)
        VALUES (?, ?, ?, ?);
        """, settings)

        # 22. NOTIFICATIONS
        notifs = [
            (user_ids[0], "Hoàn thành tối ưu lộ trình 28 đơn hàng", "EcoLogix AI vừa lập xong tuyến liên vùng TP.HCM - Bình Dương - Đồng Nai. Tiết kiệm 18.4% nhiên liệu.", "success", 0),
            (user_ids[0], "Cảnh báo tồn kho an toàn SKU-001", "Nước ngọt lon 330ml tại Kho Thủ Đức còn 75 thùng (dưới ngưỡng an toàn 95 thùng). Đề xuất đặt thêm 150 thùng.", "warning", 0),
            (user_ids[0], "Giờ cấm tải nội đô sắp bắt đầu", "Khung giờ cấm tải 16:00 - 18:00. Hệ thống tự động điều phối đơn Quận 1/3/5 ra ngoài khung giờ cấm.", "info", 0),
            (user_ids[0], "Báo cáo ESG Tháng 11/2026 sẵn sàng", "Đã tổng hợp báo cáo phát thải Scope 1: Đạt điểm Xanh 95.2%.", "success", 1),
        ]
        cursor.executemany("""
        INSERT INTO notifications (user_id, title, message, type, is_read)
        VALUES (?, ?, ?, ?, ?);
        """, notifs)

        # 23. ACTIVITY LOGS
        logs = [
            (user_ids[0], "OPTIMIZE_ROUTE", "routes", 1, "Hoàn thành tối ưu lộ trình RT-2026-1101 (42.8 km, giảm 18% nhiên liệu)"),
            (user_ids[0], "LOW_STOCK_ALERT", "inventory", 1, "Cảnh báo SKU-001 dưới ngưỡng Safety Stock tại Kho Tổng Thủ Đức"),
            (user_ids[1], "DISPATCH_VEHICLE", "vehicles", 3, "Điều phối Xe Tải 5 Tấn #03 chạy tuyến Biên Hòa - Bình Dương"),
            (user_ids[2], "GENERATE_ESG_REPORT", "esg_reports", 5, "Hoàn tất báo cáo kiểm toán Net-Zero Scope 1 chuẩn GHG Protocol"),
        ]
        cursor.executemany("""
        INSERT INTO activity_logs (user_id, action, entity, entity_id, details)
        VALUES (?, ?, ?, ?, ?);
        """, logs)

    print("✅ Đã seed dữ liệu mẫu liên kết đầy đủ cho toàn bộ 24 bảng của EcoLogix AI!")


if __name__ == "__main__":
    seed_all()
