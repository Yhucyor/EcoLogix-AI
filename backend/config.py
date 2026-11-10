"""
================================================================================
EcoLogix AI - File Cấu Hình Dự Án Chuẩn Bị Cho Vòng Chung Kết (Live-Code 15 Phút)
Đề tài: Nền Tảng Multi-Agent AI Tối Ưu Chuỗi Cung Ứng & Logistics Xanh Cho SMEs
Cuộc thi: AI IN ECONOMICS 2026 - Khoa Kinh tế HCM-UTE & CLB ESCUTE
================================================================================
KỊCH BẢN 15 PHÚT TỎA SÁNG TRƯỚC BAN GIÁM KHẢO:
Khi BGK đặt câu hỏi: "Nếu giá xăng tăng 15% hoặc thành phố siết giờ cấm tải từ 15:00 - 19:00,
chi phí vận hành và phương án điều xe thay đổi thế nào?",
Đội thi chỉ cần cập nhật các biến số dưới đây hoặc dùng tab Live-Code trong Cài đặt!
================================================================================
"""
import importlib
import os
import sys

# ==============================================================================
# 0. CẤU HÌNH MÔI TRƯỜNG, BẢO MẬT & SERVER
# ==============================================================================
SECRET_KEY = os.environ.get("ECOLOGIX_SECRET_KEY", "ecologix-ai-2026-hcmute-dev-secret-change-in-prod")
STRICT_AUTH = os.environ.get("ECOLOGIX_STRICT_AUTH", "false").strip().lower() in ("1", "true", "yes")
CORS_ORIGINS = [o.strip() for o in os.environ.get("ECOLOGIX_CORS_ORIGINS", "*").split(",") if o.strip()]
CONTACT_RECIPIENT_EMAIL = os.environ.get("ECOLOGIX_CONTACT_EMAIL", "geroolyhuicy@gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")

# ==============================================================================
# 1. CÁC BIẾN SỐ KINH TẾ & THAM SỐ VẬN HÀNH (LIVE-CODE 15 PHÚT)
# ==============================================================================

# Giá xăng/dầu cơ sở (VNĐ / Lít) - Mặc định Diesel / RON 95
FUEL_PRICE_PER_LITER = 23500

# Thuế phát thải Carbon (VNĐ / kg CO2) theo định hướng Net-Zero ESG Việt Nam
CARBON_TAX_RATE = 500

# Tải trọng tối đa mỗi xe tải nhẹ đô thị tiêu chuẩn (kg)
MAX_VEHICLE_LOAD_KG = 1500

# Khung giờ cấm xe tải lưu thông vào khu vực nội đô TP.HCM (Quận 1, 3, 5, 10...)
RESTRICTED_TIME_WINDOW = ["16:00", "18:00"]

# ==============================================================================
# 2. HỆ SỐ KỸ THUẬT VẬN TẢI & PHÁT THẢI ESG
# ==============================================================================

# Mức tiêu hao nhiên liệu trung bình đô thị (Lít / 100 km)
FUEL_CONSUMPTION_PER_100KM = 11.5

# Hệ số phát thải CO2 (kg CO2 sinh ra từ 1 lít dầu Diesel)
CO2_FACTOR_PER_LITER = 2.68

# Chi phí nhân công tài xế & khấu hao xe cơ bản (VNĐ / km)
DRIVER_AND_DEPRECIATION_PER_KM = 3800

# Tiền phạt / chi phí cơ hội nếu vi phạm giờ cấm tải (VNĐ / chuyến)
RESTRICTED_VIOLATION_PENALTY = 2500000

# ==============================================================================
# 3. THIẾT LẬP KHO TỔNG (DEPOT) & ĐỘI XE
# ==============================================================================

DEPOT_LOCATION = {
    "name": "Kho Tổng EcoLogix Logistics Hub (TP. Thủ Đức)",
    "lat": 10.8505,
    "lng": 106.7718,
    "address": "Khu Công Nghệ Cao, TP. Thủ Đức, TP.HCM"
}

VEHICLES_CONFIG = [
    {
        "id": "XE-01",
        "name": "Xe Tải Eco 1.5T #01",
        "type": "Tải nhẹ Thaco Towner",
        "capacity_kg": 1500,
        "fuel_type": "Diesel",
        "color": "#10B981",
        "status": "Khả dụng"
    },
    {
        "id": "XE-02",
        "name": "Xe Tải Eco 2.5T #02",
        "type": "Tải trung Isuzu Forward",
        "capacity_kg": 2500,
        "fuel_type": "Diesel",
        "color": "#3B82F6",
        "status": "Khả dụng"
    },
    {
        "id": "XE-03",
        "name": "Xe Điện Eco Electric 1.2T #03",
        "type": "EV Van GreenSpeed",
        "capacity_kg": 1200,
        "fuel_type": "Electric",
        "color": "#8B5CF6",
        "status": "Khả dụng (Ưu tiên Net-Zero)"
    }
]


# ==============================================================================
# 4. HÀM TÍNH TOÁN LẠI CHI PHÍ TỨC THÌ & CẬP NHẬT LIVE-CODE
# ==============================================================================

def update_operational_cost(
    fuel_price: float = None,
    carbon_tax: float = None,
    distance_km: float = 120.0,
    is_restricted_violation: bool = False,
    fuel_consumption_per_100km: float = None,
    is_electric: bool = False,
):
    """
    Hàm tính toán lại chi phí vận tải tức thì khi BGK đưa ra câu hỏi phụ tại Vòng Chung kết.
    Hỗ trợ phân biệt xe dầu Diesel và xe điện EV Net-Zero.
    """
    actual_fuel_price = fuel_price if fuel_price is not None else FUEL_PRICE_PER_LITER
    actual_carbon_tax = carbon_tax if carbon_tax is not None else CARBON_TAX_RATE
    consumption_rate = (
        fuel_consumption_per_100km
        if fuel_consumption_per_100km is not None
        else FUEL_CONSUMPTION_PER_100KM
    )

    if is_electric:
        # Xe điện tiêu thụ ~28 kWh/100km, giá điện ~3,000 VNĐ/kWh, 0 phát thải ống xả Scope 1
        kwh_needed = (distance_km / 100.0) * 28.0
        fuel_needed = 0.0
        fuel_cost = kwh_needed * 3000.0
        co2_emission_kg = 0.0
        carbon_tax_cost = 0.0
    else:
        fuel_needed = (distance_km / 100.0) * consumption_rate
        fuel_cost = fuel_needed * actual_fuel_price
        co2_emission_kg = fuel_needed * CO2_FACTOR_PER_LITER
        carbon_tax_cost = co2_emission_kg * actual_carbon_tax

    maintenance_cost = distance_km * DRIVER_AND_DEPRECIATION_PER_KM
    penalty_cost = RESTRICTED_VIOLATION_PENALTY if is_restricted_violation else 0
    total_cost = fuel_cost + carbon_tax_cost + maintenance_cost + penalty_cost

    return {
        "distance_km": round(distance_km, 2),
        "fuel_needed_liters": round(fuel_needed, 2),
        "fuel_cost_vnd": round(fuel_cost, 0),
        "co2_emission_kg": round(co2_emission_kg, 2),
        "carbon_tax_cost_vnd": round(carbon_tax_cost, 0),
        "maintenance_cost_vnd": round(maintenance_cost, 0),
        "penalty_cost_vnd": penalty_cost,
        "total_cost_vnd": round(total_cost, 0),
        "applied_fuel_price": actual_fuel_price,
        "applied_carbon_tax": actual_carbon_tax,
        "restricted_window": list(RESTRICTED_TIME_WINDOW),
    }


def save_live_config(
    fuel_price: int,
    carbon_tax: int,
    max_load_kg: int,
    restricted_start: str,
    restricted_end: str,
):
    """Cập nhật an toàn các hằng số Live-Code ngay trong file config.py hiện tại và reload module."""
    config_path = os.path.abspath(__file__)
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    replacements = {
        "FUEL_PRICE_PER_LITER =": f"FUEL_PRICE_PER_LITER = {int(fuel_price)}\n",
        "CARBON_TAX_RATE =": f"CARBON_TAX_RATE = {int(carbon_tax)}\n",
        "MAX_VEHICLE_LOAD_KG =": f"MAX_VEHICLE_LOAD_KG = {int(max_load_kg)}\n",
        "RESTRICTED_TIME_WINDOW =": f'RESTRICTED_TIME_WINDOW = ["{restricted_start}", "{restricted_end}"]\n',
    }

    updated_lines = []
    for line in lines:
        replaced = False
        for prefix, new_line in replacements.items():
            if line.startswith(prefix):
                updated_lines.append(new_line)
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

    importlib.reload(sys.modules[__name__])
    return get_config_snapshot()


def get_config_snapshot():
    """Trả về dictionary cấu hình hiện hành để đồng bộ API, UI và DB."""
    return {
        "fuel_price_per_liter": FUEL_PRICE_PER_LITER,
        "carbon_tax_rate": CARBON_TAX_RATE,
        "max_vehicle_load_kg": MAX_VEHICLE_LOAD_KG,
        "restricted_time_window": list(RESTRICTED_TIME_WINDOW),
        "fuel_consumption_per_100km": FUEL_CONSUMPTION_PER_100KM,
        "co2_factor_per_liter": CO2_FACTOR_PER_LITER,
        "driver_and_depreciation_per_km": DRIVER_AND_DEPRECIATION_PER_KM,
        "restricted_violation_penalty": RESTRICTED_VIOLATION_PENALTY,
        "depot": DEPOT_LOCATION,
    }
