"""
Script sinh 100 điểm giao hàng giả lập (Dummy Data) chuẩn thực tế tại TP.HCM và Đồng Nai.
Phục vụ Demo Vòng 2 & Kịch bản Vòng Chung kết AI IN ECONOMICS 2026.
"""
import json
import os
import random
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Điểm xuất phát (Depot): KCNC Thủ Đức
DEPOT_LAT, DEPOT_LNG = 10.8505, 106.7718

# Các cụm địa điểm trọng điểm TP.HCM & Đồng Nai
AREAS = [
    # TP.HCM - Khu vực nội đô (Chịu cấm tải 16h-18h)
    {"name_prefix": "Đại lý Tạp hóa & Bách hóa Q1", "district": "Quận 1", "province": "TP.HCM", "lat_center": 10.7769, "lng_center": 106.7009, "restricted": True, "count": 12},
    {"name_prefix": "Siêu thị Mini Tiện lợi Q3", "district": "Quận 3", "province": "TP.HCM", "lat_center": 10.7828, "lng_center": 106.6872, "restricted": True, "count": 10},
    {"name_prefix": "Nhà thuốc & Tiệm tạp hóa Q5", "district": "Quận 5", "province": "TP.HCM", "lat_center": 10.7554, "lng_center": 106.6669, "restricted": True, "count": 8},
    {"name_prefix": "Cửa hàng phân phối Q10", "district": "Quận 10", "province": "TP.HCM", "lat_center": 10.7725, "lng_center": 106.6672, "restricted": True, "count": 8},
    
    # TP.HCM - Khu vực ven & TP. Thủ Đức (Không cấm tải)
    {"name_prefix": "Điểm bán lẻ Thảo Điền", "district": "TP. Thủ Đức", "province": "TP.HCM", "lat_center": 10.8062, "lng_center": 106.7351, "restricted": False, "count": 10},
    {"name_prefix": "Chuỗi bách hóa Linh Trung", "district": "TP. Thủ Đức", "province": "TP.HCM", "lat_center": 10.8655, "lng_center": 106.7825, "restricted": False, "count": 10},
    {"name_prefix": "Tổng kho Bán lẻ Bình Tân", "district": "Bình Tân", "province": "TP.HCM", "lat_center": 10.7456, "lng_center": 106.6052, "restricted": False, "count": 8},
    {"name_prefix": "Cửa hàng tiện ích Gò Vấp", "district": "Gò Vấp", "province": "TP.HCM", "lat_center": 10.8388, "lng_center": 106.6653, "restricted": False, "count": 8},
    
    # Đồng Nai - Biên Hòa & Khu Công Nghiệp
    {"name_prefix": "Đại lý phân phối Tân Mai", "district": "Biên Hòa", "province": "Đồng Nai", "lat_center": 10.9574, "lng_center": 106.8427, "restricted": False, "count": 8},
    {"name_prefix": "Kho vệ tinh KCN Amata", "district": "Biên Hòa", "province": "Đồng Nai", "lat_center": 10.9423, "lng_center": 106.8833, "restricted": False, "count": 6},
    {"name_prefix": "Cửa hàng tổng hợp Long Thành", "district": "Long Thành", "province": "Đồng Nai", "lat_center": 10.7932, "lng_center": 106.9538, "restricted": False, "count": 6},
    {"name_prefix": "Trạm trung chuyển Nhơn Trạch", "district": "Nhơn Trạch", "province": "Đồng Nai", "lat_center": 10.7250, "lng_center": 106.8920, "restricted": False, "count": 6},
]

random.seed(2026) # Đảm bảo reproducibility

delivery_points = []
point_id = 1

TIME_WINDOWS = [
    {"label": "Sáng sớm", "start": "07:30", "end": "11:30"},
    {"label": "Đầu giờ chiều", "start": "13:00", "end": "16:00"},
    {"label": "Chiều tan tầm", "start": "16:00", "end": "18:00"},
    {"label": "Tối", "start": "18:30", "end": "21:30"},
]

for area in AREAS:
    for i in range(area["count"]):
        # Độ nhiễu tọa độ (~1.5 - 3 km quanh trung tâm)
        lat = round(area["lat_center"] + random.uniform(-0.015, 0.015), 6)
        lng = round(area["lng_center"] + random.uniform(-0.015, 0.015), 6)
        demand = random.choice([40, 55, 70, 85, 100, 120, 150, 180, 220, 260])
        tw = random.choice(TIME_WINDOWS)
        
        # Nếu ở khu nội đô và khung giờ rơi vào 16:00 - 18:00 -> cờ cảnh báo
        is_restricted_risk = area["restricted"] and (tw["label"] == "Chiều tan tầm")
        
        point = {
            "id": f"DELIV-{point_id:03d}",
            "name": f"{area['name_prefix']} #{i+1:02d}",
            "district": area["district"],
            "province": area["province"],
            "lat": lat,
            "lng": lng,
            "demand_kg": demand,
            "time_window_start": tw["start"],
            "time_window_end": tw["end"],
            "time_window_label": tw["label"],
            "is_urban_restricted": area["restricted"],
            "is_peak_hour_risk": is_restricted_risk,
            "priority": random.choice(["Cao (Hàng dễ hỏng)", "Tiêu chuẩn", "Tiêu chuẩn", "Linh hoạt"])
        }
        delivery_points.append(point)
        point_id += 1

# Đảm bảo đúng 100 điểm
delivery_points = delivery_points[:100]

with open(os.path.join(DATA_DIR, "delivery_points_100.json"), "w", encoding="utf-8") as f:
    json.dump(delivery_points, f, ensure_ascii=False, indent=2)

df = pd.DataFrame(delivery_points)
df.to_csv(os.path.join(DATA_DIR, "delivery_points_100.csv"), index=False, encoding="utf-8-sig")

print(f"✅ Đã tạo thành công bộ dữ liệu 100 điểm giao hàng: {len(delivery_points)} điểm.")
print(f"   - Số điểm tại TP.HCM: {len(df[df['province'] == 'TP.HCM'])}")
print(f"   - Số điểm tại Đồng Nai: {len(df[df['province'] == 'Đồng Nai'])}")
print(f"   - Số điểm trong khu vực nội đô cấm tải: {len(df[df['is_urban_restricted'] == True])}")

