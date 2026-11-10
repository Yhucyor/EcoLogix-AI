"""
EcoLogix AI - Vehicle & Fleet Management Service
Quản lý phương tiện vận tải, hiệu suất chạy xe & thống kê phát thải theo xe (Full CRUD).
"""
from typing import Tuple
from database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from utils.helpers import log_activity
from utils.validators import validate_non_empty, validate_positive


def get_vehicles_with_stats() -> list:
    return rows_to_dicts(execute_query("""
    SELECT v.*,
           COALESCE(COUNT(r.id), 0) as total_routes,
           COALESCE(ROUND(SUM(r.total_distance_km), 1), 0) as total_distance_km,
           COALESCE(ROUND(SUM(r.co2_emission_kg), 1), 0) as total_co2_kg,
           COALESCE(ROUND(SUM(r.fuel_consumed_liters), 1), 0) as total_fuel_liters,
           COALESCE(ROUND(SUM(r.total_cost_vnd), 0), 0) as total_cost_vnd
    FROM vehicles v
    LEFT JOIN routes r ON v.id = r.vehicle_id
    GROUP BY v.id
    ORDER BY v.id ASC;
    """))


def add_vehicle(plate_number: str, vehicle_name: str, vehicle_type: str, max_load_kg: float, fuel_type: str, fuel_consumption: float, cost_per_km: float, user_id: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_non_empty(plate_number, "Biển số xe")
    if not ok:
        return False, msg
    ok, msg = validate_non_empty(vehicle_name, "Tên phương tiện")
    if not ok:
        return False, msg
    ok, msg = validate_positive(max_load_kg, "Tải trọng tối đa")
    if not ok:
        return False, msg

    if execute_query("SELECT id FROM vehicles WHERE LOWER(plate_number) = LOWER(?);", (plate_number.strip(),)):
        return False, f"Biển số xe `{plate_number}` đã tồn tại."

    v_id = execute_insert(
        """
        INSERT INTO vehicles (company_id, plate_number, vehicle_name, vehicle_type, max_load_kg, fuel_type, fuel_consumption_per_100km, operational_cost_per_km, status)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, 'Available');
        """,
        (plate_number.strip().upper(), vehicle_name.strip(), vehicle_type, float(max_load_kg), fuel_type, float(fuel_consumption), float(cost_per_km)),
    )
    log_activity(user_id, "CREATE_VEHICLE", "vehicles", v_id, f"Thêm xe {vehicle_name} ({plate_number})")
    return True, f"Đã thêm phương tiện `{vehicle_name}`!"


def update_vehicle(vehicle_id: int, vehicle_name: str, vehicle_type: str, max_load_kg: float, fuel_type: str, fuel_consumption: float, cost_per_km: float, status: str, user_id: int = 1) -> Tuple[bool, str]:
    execute_update(
        """
        UPDATE vehicles
        SET vehicle_name = ?, vehicle_type = ?, max_load_kg = ?, fuel_type = ?,
            fuel_consumption_per_100km = ?, operational_cost_per_km = ?, status = ?
        WHERE id = ?;
        """,
        (vehicle_name.strip(), vehicle_type, float(max_load_kg), fuel_type, float(fuel_consumption), float(cost_per_km), status, vehicle_id),
    )
    log_activity(user_id, "UPDATE_VEHICLE", "vehicles", vehicle_id, f"Cập nhật xe #{vehicle_id} ({status})")
    return True, "Đã cập nhật thông tin phương tiện."


def update_vehicle_status(plate_or_id, status: str, user_id: int = 1) -> Tuple[bool, str]:
    if isinstance(plate_or_id, int) or str(plate_or_id).isdigit():
        cnt = execute_update("UPDATE vehicles SET status = ? WHERE id = ?;", (status, int(plate_or_id)))
    else:
        cnt = execute_update("UPDATE vehicles SET status = ? WHERE plate_number = ?;", (status, str(plate_or_id)))
    if cnt == 0:
        return False, "Không tìm thấy phương tiện."
    log_activity(user_id, "VEHICLE_STATUS", "vehicles", None, f"Xe {plate_or_id} -> {status}")
    return True, f"Đã đổi trạng thái xe `{plate_or_id}` thành `{status}`."


def delete_vehicle(vehicle_id: int, user_id: int = 1) -> Tuple[bool, str]:
    used = execute_query("SELECT COUNT(*) as cnt FROM routes WHERE vehicle_id = ?;", (vehicle_id,))
    if used and used[0]["cnt"] > 0:
        return False, "Không thể xóa phương tiện đang có lịch sử tuyến vận tải (hãy chuyển sang Bảo trì)."
    cnt = execute_update("DELETE FROM vehicles WHERE id = ?;", (vehicle_id,))
    if cnt == 0:
        return False, "Không tìm thấy phương tiện."
    log_activity(user_id, "DELETE_VEHICLE", "vehicles", vehicle_id, f"Xóa xe #{vehicle_id}")
    return True, "Đã xóa phương tiện khỏi đội xe."

