"""
Fix and initialize multi-tenant companies and assign user 5 (thucyent09@gmail.com) to Company 2.
"""
import sys
from backend.database.connection import execute_query, execute_insert, execute_update, get_db_dialect
from backend.database.models import init_database
from backend.database.seed import seed_starter_company_data

def run():
    dialect = get_db_dialect()
    print(f"Connecting to DB ({dialect})...")
    init_database()

    # 1. Restore Company 1 name
    execute_update(
        """
        UPDATE companies
        SET name = 'Công Ty TNHH Phân Phối & Logistics Xanh EcoLogix',
            tax_code = '0317892345',
            address = 'Khu Công Nghệ Cao, P. Tăng Nhơn Phú B, TP. Thủ Đức',
            city = 'TP. Hồ Chí Minh',
            phone = '028 3896 5555',
            email = 'contact@ecologix.vn',
            industry = 'Phân phối Hàng tiêu dùng (FMCG) & Logistics',
            size = 'SMEs (50-100 nhân sự)'
        WHERE id = 1;
        """
    )
    print("✅ Đã khôi phục thông tin Công ty 1 (EcoLogix Logistics).")

    # 2. Check if Company 2 exists, otherwise create it
    c2 = execute_query("SELECT id, name FROM companies WHERE id = 2;")
    if not c2:
        c2_id = execute_insert(
            """
            INSERT INTO companies (id, name, tax_code, industry, size, address, city, phone, email)
            VALUES (2, 'Công Ty TNHH Phân Phối Hàng Tiêu Dùng Sài Gòn', '0318992211', 'Phân phối hàng tiêu dùng (FMCG)', 'Doanh nghiệp nhỏ (10 - 50 nhân viên)', 'Khu Công Nghệ Cao, TP. Thủ Đức', 'TP. Hồ Chí Minh', '0908123456', 'thucyent09@gmail.com');
            """
        )
        print(f"✅ Đã tạo mới Công ty 2 (ID: {c2_id}).")
    else:
        print("ℹ️ Công ty 2 đã tồn tại.")

    # 3. Assign User 5 to Company 2
    u5 = execute_query("SELECT id, email, company_id FROM users WHERE email = 'thucyent09@gmail.com';")
    if u5:
        execute_update("UPDATE users SET company_id = 2, has_company = 1 WHERE id = ?;", (u5[0]["id"],))
        print(f"✅ Đã chuyển tài khoản {u5[0]['email']} sang Công ty 2 (ID: 2).")

    # 4. Seed starter data for Company 2
    seed_starter_company_data(2, "Công Ty TNHH Phân Phối Hàng Tiêu Dùng Sài Gòn", admin_user_id=5 if u5 else 1)
    print("✅ Đã seed đầy đủ dữ liệu vận hành khởi đầu độc lập cho Công ty 2!")

    # 5. Verify users and companies
    users = execute_query("SELECT id, company_id, name, email, role FROM users;")
    companies = execute_query("SELECT id, name FROM companies;")
    print("\n--- DANH SÁCH DOANH NGHIỆP ---")
    for c in companies:
        print(f"🏢 [{c['id']}] {c['name']}")
    print("\n--- DANH SÁCH TÀI KHOẢN & DOANH NGHIỆP TRỰC THUỘC ---")
    for u in users:
        print(f"👤 [{u['id']}] {u['name']} ({u['email']}) -> Công ty ID: {u['company_id']}")

if __name__ == "__main__":
    run()
