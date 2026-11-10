"""
EcoLogix AI - Database Schema DDL & Lightweight Migration
Khởi tạo đầy đủ 24 bảng nghiệp vụ liên kết chặt chẽ, thiết kế sẵn sàng mở rộng sang PostgreSQL.
"""
from backend.database.connection import get_db

SCHEMA_SQL = """
-- 1. COMPANIES
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tax_code TEXT UNIQUE,
    industry TEXT,
    size TEXT,
    address TEXT,
    city TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ROLES
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT
);

-- 3. USERS
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'Manager',
    avatar_url TEXT,
    phone TEXT,
    is_verified INTEGER DEFAULT 1,
    reset_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 4. WAREHOUSES
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    code TEXT UNIQUE,
    address TEXT,
    lat REAL,
    lng REAL,
    capacity_m3 REAL,
    current_utilization_pct REAL,
    is_central_hub INTEGER DEFAULT 0,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 5. PRODUCTS
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT,
    unit_price REAL,
    weight_kg REAL,
    min_stock INTEGER,
    max_stock INTEGER,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 6. INVENTORY
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER,
    product_id INTEGER,
    quantity INTEGER DEFAULT 0,
    safety_stock INTEGER DEFAULT 50,
    reorder_point INTEGER DEFAULT 120,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
    FOREIGN KEY(product_id) REFERENCES products(id),
    UNIQUE(warehouse_id, product_id)
);

-- 7. INVENTORY TRANSACTIONS
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    warehouse_id INTEGER,
    transaction_type TEXT, -- 'IN', 'OUT', 'TRANSFER', 'ADJUST'
    quantity INTEGER,
    reference_code TEXT,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

-- 8. CUSTOMERS
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    district TEXT,
    province TEXT,
    lat REAL,
    lng REAL,
    customer_tier TEXT DEFAULT 'Standard',
    total_spent REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 9. SUPPLIERS
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    products_supplied TEXT,
    debt_vnd REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 10. VEHICLES
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    plate_number TEXT UNIQUE NOT NULL,
    vehicle_name TEXT NOT NULL,
    vehicle_type TEXT,
    max_load_kg REAL,
    fuel_type TEXT,
    fuel_consumption_per_100km REAL,
    operational_cost_per_km REAL,
    status TEXT DEFAULT 'Available', -- 'Available', 'In Transit', 'Maintenance'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 11. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    order_code TEXT UNIQUE NOT NULL,
    customer_id INTEGER,
    warehouse_id INTEGER,
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'SHIPPING', 'COMPLETED', 'CANCELLED'
    total_weight_kg REAL,
    total_amount REAL,
    shipping_fee REAL,
    time_window_start TEXT,
    time_window_end TEXT,
    is_urban_restricted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
);

-- 12. ORDER ITEMS
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- 13. ROUTES
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_code TEXT UNIQUE NOT NULL,
    vehicle_id INTEGER,
    route_date DATE,
    status TEXT DEFAULT 'Optimized',
    total_distance_km REAL,
    baseline_distance_km REAL DEFAULT 0,
    saved_distance_km REAL DEFAULT 0,
    total_time_hours REAL,
    fuel_consumed_liters REAL,
    fuel_saved_liters REAL DEFAULT 0,
    co2_emission_kg REAL,
    saved_co2_kg REAL DEFAULT 0,
    total_cost_vnd REAL,
    saved_cost_vnd REAL DEFAULT 0,
    is_optimized INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);

-- 14. ROUTE STOPS
CREATE TABLE IF NOT EXISTS route_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    order_id INTEGER,
    stop_sequence INTEGER,
    arrival_time TEXT,
    departure_time TEXT,
    lat REAL,
    lng REAL,
    address TEXT,
    FOREIGN KEY(route_id) REFERENCES routes(id),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

-- 15. FORECASTS
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    forecast_date DATE,
    predicted_demand INTEGER,
    actual_demand INTEGER,
    confidence_lower INTEGER,
    confidence_upper INTEGER,
    horizon_days INTEGER DEFAULT 30,
    safety_stock INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 0,
    accuracy_pct REAL DEFAULT 94.0,
    model_name TEXT DEFAULT 'LightGBM Regressor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- 16. AI AGENTS
CREATE TABLE IF NOT EXISTS ai_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    model_name TEXT DEFAULT 'EcoLogix-Agentic-LLM',
    status TEXT DEFAULT 'Active'
);

-- 17. AI CONVERSATIONS
CREATE TABLE IF NOT EXISTS ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- 18. AI MESSAGES
CREATE TABLE IF NOT EXISTS ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    sender TEXT NOT NULL, -- 'user', 'assistant'
    agent_name TEXT,
    content TEXT NOT NULL,
    reasoning_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id)
);

-- 19. EXPENSES
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    category TEXT, -- 'fuel', 'labor', 'storage', 'maintenance', 'carbon_tax'
    amount_vnd REAL,
    expense_date DATE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 20. CARBON EMISSIONS
CREATE TABLE IF NOT EXISTS carbon_emissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    co2_kg REAL,
    fuel_liters REAL,
    calculation_date DATE,
    standard TEXT DEFAULT 'GHG Protocol Scope 1',
    FOREIGN KEY(route_id) REFERENCES routes(id)
);

-- 21. ESG REPORTS
CREATE TABLE IF NOT EXISTS esg_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    month INTEGER,
    year INTEGER,
    total_co2_kg REAL,
    co2_saved_kg REAL,
    green_logistics_score REAL,
    report_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- 22. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info', -- 'info', 'warning', 'success', 'danger'
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- 23. SYSTEM SETTINGS
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id),
    UNIQUE(company_id, setting_key)
);

-- 24. ACTIVITY LOGS
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def _ensure_column(cursor, table: str, column: str, definition: str):
    """Thêm cột còn thiếu cho database hiện có mà không làm mất dữ liệu."""
    cursor.execute(f"PRAGMA table_info({table});")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")


def init_database():
    """Khởi tạo toàn bộ 24 bảng và nâng cấp cột bổ sung an toàn."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        cur = conn.cursor()
        _ensure_column(cur, "users", "is_verified", "INTEGER DEFAULT 1")
        _ensure_column(cur, "users", "reset_token", "TEXT")
        _ensure_column(cur, "routes", "baseline_distance_km", "REAL DEFAULT 0")
        _ensure_column(cur, "routes", "saved_distance_km", "REAL DEFAULT 0")
        _ensure_column(cur, "routes", "fuel_saved_liters", "REAL DEFAULT 0")
        _ensure_column(cur, "routes", "saved_co2_kg", "REAL DEFAULT 0")
        _ensure_column(cur, "routes", "saved_cost_vnd", "REAL DEFAULT 0")
        _ensure_column(cur, "forecasts", "horizon_days", "INTEGER DEFAULT 30")
        _ensure_column(cur, "forecasts", "safety_stock", "INTEGER DEFAULT 0")
        _ensure_column(cur, "forecasts", "reorder_point", "INTEGER DEFAULT 0")
        _ensure_column(cur, "forecasts", "accuracy_pct", "REAL DEFAULT 94.0")
    print("✅ Đã khởi tạo & đồng bộ schema 24 bảng dữ liệu cho EcoLogix AI.")


if __name__ == "__main__":
    init_database()
