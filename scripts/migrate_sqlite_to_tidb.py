"""
EcoLogix AI - One-time Migration Script (SQLite -> TiDB Cloud)
Khởi tạo schema 24 bảng trên TiDB Cloud và đồng bộ toàn bộ dữ liệu từ `backend/database/ecologix.db`.
Chạy: `python scripts/migrate_sqlite_to_tidb.py`
"""
import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database.connection import DEFAULT_DB_FILE, get_db, is_tidb_enabled
from backend.database.models import init_database

TABLE_ORDER = [
    "companies",
    "roles",
    "users",
    "warehouses",
    "products",
    "inventory",
    "inventory_transactions",
    "customers",
    "suppliers",
    "vehicles",
    "orders",
    "order_items",
    "routes",
    "route_stops",
    "forecasts",
    "ai_agents",
    "ai_conversations",
    "ai_messages",
    "expenses",
    "carbon_emissions",
    "esg_reports",
    "notifications",
    "system_settings",
    "activity_logs",
]


def migrate(sqlite_path: str = DEFAULT_DB_FILE):
    if not is_tidb_enabled():
        raise RuntimeError("Chưa cấu hình TIDB_HOST trong .env hoặc biến môi trường (lưu ý không đặt ECOLOGIX_DB_PATH).")
    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError(f"Không tìm thấy file SQLite nguồn: {sqlite_path}")

    init_database()

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    migrated_counts = {}

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in reversed(TABLE_ORDER):
                cur.execute(f"DELETE FROM {table};")

            for table in TABLE_ORDER:
                s_cur = src.cursor()
                s_cur.execute(f"SELECT * FROM {table};")
                rows = s_cur.fetchall()
                if not rows:
                    cur.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1;")
                    migrated_counts[table] = 0
                    continue

                cols = list(rows[0].keys())
                col_list = ", ".join(f"`{c}`" for c in cols)
                placeholders = ", ".join(["?"] * len(cols))
                values = [tuple(r[c] for c in cols) for r in rows]
                cur.executemany(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders});", values)

                max_id = max((int(r["id"]) for r in rows if "id" in r.keys() and r["id"] is not None), default=0)
                cur.execute(f"ALTER TABLE {table} AUTO_INCREMENT = {max_id + 1};")
                migrated_counts[table] = len(rows)

            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    finally:
        src.close()

    total = sum(migrated_counts.values())
    print(f"✅ Đã đồng bộ {total} bản ghi qua {len(TABLE_ORDER)} bảng từ SQLite lên TiDB Cloud:")
    for t, c in migrated_counts.items():
        print(f"   - {t}: {c}")


if __name__ == "__main__":
    migrate()

