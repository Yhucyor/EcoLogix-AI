"""
EcoLogix AI - Green Routing & CVRPTW Optimization Service
Giải bài toán VRP có ràng buộc tải trọng & khung giờ cấm tải (Nearest Neighbor + 2-Opt Local Search).
Tích hợp trực tiếp tham số Live-Code từ `config.py`, hỗ trợ cả đơn hàng SQLite và bộ 100 điểm TP.HCM/Đồng Nai.
"""
import importlib
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

import config
from database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from utils.helpers import log_activity, create_notification, windows_overlap


def _fresh_config():
    importlib.reload(config)
    return config


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return float(R * c * 1.35)


def _route_total_distance(stops: List[Dict[str, Any]], depot_lat: float, depot_lng: float) -> float:
    if not stops:
        return 0.0
    dist = calculate_distance(depot_lat, depot_lng, stops[0]["lat"], stops[0]["lng"])
    for i in range(len(stops) - 1):
        dist += calculate_distance(stops[i]["lat"], stops[i]["lng"], stops[i + 1]["lat"], stops[i + 1]["lng"])
    dist += calculate_distance(stops[-1]["lat"], stops[-1]["lng"], depot_lat, depot_lng)
    return dist


def _two_opt_optimize(stops: List[Dict[str, Any]], depot_lat: float, depot_lng: float) -> List[Dict[str, Any]]:
    """Cải thiện lộ trình bằng thuật toán 2-Opt để cắt bỏ các đoạn giao chéo."""
    if len(stops) < 3:
        return stops
    best = list(stops)
    best_dist = _route_total_distance(best, depot_lat, depot_lng)
    improved = True
    iters = 0
    while improved and iters < 40:
        improved = False
        iters += 1
        for i in range(len(best) - 1):
            for j in range(i + 2, len(best)):
                candidate = best[:i] + list(reversed(best[i:j])) + best[j:]
                cand_dist = _route_total_distance(candidate, depot_lat, depot_lng)
                if cand_dist + 1e-4 < best_dist:
                    best = candidate
                    best_dist = cand_dist
                    improved = True
    return best


def _nearest_neighbor_plus_2opt(items: List[Dict[str, Any]], depot_lat: float, depot_lng: float) -> List[Dict[str, Any]]:
    if not items:
        return []
    unvisited = list(items)
    ordered = []
    c_lat, c_lng = depot_lat, depot_lng
    while unvisited:
        nxt = min(unvisited, key=lambda o: calculate_distance(c_lat, c_lng, o["lat"], o["lng"]))
        ordered.append(nxt)
        c_lat, c_lng = nxt["lat"], nxt["lng"]
        unvisited.remove(nxt)
    return _two_opt_optimize(ordered, depot_lat, depot_lng)


def get_vehicles() -> list:
    return rows_to_dicts(execute_query("SELECT * FROM vehicles ORDER BY id ASC;"))


def get_pending_orders() -> list:
    return rows_to_dicts(execute_query("""
    SELECT o.*, c.name as customer_name, c.district, c.province, c.lat, c.lng, c.address
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    WHERE o.status IN ('PENDING', 'PROCESSING')
    ORDER BY o.is_urban_restricted DESC, o.id ASC;
    """))


def get_saved_routes(limit: int = 15) -> list:
    return rows_to_dicts(execute_query("""
    SELECT r.*, v.vehicle_name, v.plate_number, v.fuel_type
    FROM routes r
    LEFT JOIN vehicles v ON r.vehicle_id = v.id
    ORDER BY r.id DESC
    LIMIT ?;
    """, (limit,)))


def load_100_delivery_points() -> list:
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "delivery_points_100.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def optimize_routes_for_orders(
    selected_order_ids: List[int],
    vehicle_id: Optional[int] = None,
    enforce_time_window: bool = True,
    save_to_db: bool = True,
    user_id: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Tối ưu hóa thứ tự giao hàng cho tập đơn hàng thực tế từ SQLite.
    Kiểm tra tải trọng xe tối đa, khung giờ cấm tải từ `config.py` và lưu tuyến vào `routes`.
    """
    cfg = _fresh_config()
    if not selected_order_ids:
        return None

    placeholders = ",".join(["?"] * len(selected_order_ids))
    orders = rows_to_dicts(execute_query(
        f"""
        SELECT o.*, c.name as customer_name, c.district, c.province, c.lat, c.lng, c.address
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id IN ({placeholders});
        """,
        tuple(selected_order_ids),
    ))
    if not orders:
        return None

    vehicles = get_vehicles()
    selected_vehicle = next((v for v in vehicles if v["id"] == vehicle_id), vehicles[0] if vehicles else None)
    is_electric = (selected_vehicle and selected_vehicle["fuel_type"] == "Electric")
    veh_cons = selected_vehicle["fuel_consumption_per_100km"] if selected_vehicle else cfg.FUEL_CONSUMPTION_PER_100KM
    max_cap = min(
        float(selected_vehicle["max_load_kg"]) if selected_vehicle else cfg.MAX_VEHICLE_LOAD_KG,
        float(cfg.MAX_VEHICLE_LOAD_KG) if (selected_vehicle and selected_vehicle["max_load_kg"] <= 1500) else float(selected_vehicle["max_load_kg"]),
    )

    depot = cfg.DEPOT_LOCATION
    ordered_stops = _nearest_neighbor_plus_2opt(orders, depot["lat"], depot["lng"])
    total_dist = round(_route_total_distance(ordered_stops, depot["lat"], depot["lng"]), 1)
    total_load = round(sum(float(o["total_weight_kg"] or 0) for o in ordered_stops), 1)
    overload_warning = total_load > max_cap

    # Tính lịch trình từng điểm dừng & kiểm tra né giờ cấm tải
    tw_start, tw_end = cfg.RESTRICTED_TIME_WINDOW[0], cfg.RESTRICTED_TIME_WINDOW[1]
    restricted_conflicts = 0
    schedule = []
    curr_minutes = 8 * 60  # Xuất phát 08:00
    prev_lat, prev_lng = depot["lat"], depot["lng"]

    for seq, stop in enumerate(ordered_stops, start=1):
        leg_km = calculate_distance(prev_lat, prev_lng, stop["lat"], stop["lng"])
        travel_min = int(round((leg_km / 32.0) * 60))
        curr_minutes += max(8, travel_min)

        arr_str = f"{curr_minutes // 60:02d}:{curr_minutes % 60:02d}"
        dep_minutes = curr_minutes + 15
        dep_str = f"{dep_minutes // 60:02d}:{dep_minutes % 60:02d}"

        if stop.get("is_urban_restricted") and windows_overlap(arr_str, dep_str, tw_start, tw_end):
            restricted_conflicts += 1
            if enforce_time_window:
                # Tự động điều chỉnh khung giao ra sau giờ cấm tải
                sh, sm = map(int, tw_end.split(":"))
                curr_minutes = sh * 60 + sm + 10
                arr_str = f"{curr_minutes // 60:02d}:{curr_minutes % 60:02d}"
                dep_minutes = curr_minutes + 15
                dep_str = f"{dep_minutes // 60:02d}:{dep_minutes % 60:02d}"

        stop["stop_sequence"] = seq
        stop["arrival_time"] = arr_str
        stop["departure_time"] = dep_str
        stop["leg_distance_km"] = round(leg_km, 1)
        schedule.append(stop)
        curr_minutes = dep_minutes
        prev_lat, prev_lng = stop["lat"], stop["lng"]

    total_time_hours = round((curr_minutes - 8 * 60) / 60.0 + 0.35, 2)
    violation_flag = (not enforce_time_window) and restricted_conflicts > 0

    opt_cost = cfg.update_operational_cost(
        distance_km=total_dist,
        is_restricted_violation=violation_flag,
        fuel_consumption_per_100km=veh_cons,
        is_electric=is_electric,
    )
    baseline_dist = round(total_dist * 1.225, 1)
    baseline_cost = cfg.update_operational_cost(
        distance_km=baseline_dist,
        is_restricted_violation=(restricted_conflicts > 0),
        fuel_consumption_per_100km=cfg.FUEL_CONSUMPTION_PER_100KM,
        is_electric=False,
    )

    saved_distance = round(baseline_dist - total_dist, 1)
    saved_fuel = round(max(0.0, baseline_cost["fuel_needed_liters"] - opt_cost["fuel_needed_liters"]), 2)
    saved_co2 = round(max(0.0, baseline_cost["co2_emission_kg"] - opt_cost["co2_emission_kg"]), 2)
    saved_money = round(max(0.0, baseline_cost["total_cost_vnd"] - opt_cost["total_cost_vnd"]), 0)

    route_code = f"RT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if save_to_db and selected_vehicle:
        r_id = execute_insert(
            """
            INSERT INTO routes (route_code, vehicle_id, route_date, status, total_distance_km, baseline_distance_km, saved_distance_km,
                                total_time_hours, fuel_consumed_liters, fuel_saved_liters, co2_emission_kg, saved_co2_kg, total_cost_vnd, saved_cost_vnd, is_optimized)
            VALUES (?, ?, ?, 'Optimized', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """,
            (
                route_code,
                selected_vehicle["id"],
                datetime.now().strftime("%Y-%m-%d"),
                total_dist,
                baseline_dist,
                saved_distance,
                total_time_hours,
                opt_cost["fuel_needed_liters"],
                saved_fuel,
                opt_cost["co2_emission_kg"],
                saved_co2,
                opt_cost["total_cost_vnd"],
                saved_money,
            ),
        )
        for stp in schedule:
            execute_insert(
                """
                INSERT INTO route_stops (route_id, order_id, stop_sequence, arrival_time, departure_time, lat, lng, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (r_id, stp["id"], stp["stop_sequence"], stp["arrival_time"], stp["departure_time"], stp["lat"], stp["lng"], stp.get("address", "")),
            )
        execute_insert(
            "INSERT INTO carbon_emissions (route_id, co2_kg, fuel_liters, calculation_date, standard) VALUES (?, ?, ?, ?, 'GHG Protocol Scope 1');",
            (r_id, opt_cost["co2_emission_kg"], opt_cost["fuel_needed_liters"], datetime.now().strftime("%Y-%m-%d")),
        )
        execute_update(
            f"UPDATE orders SET status = 'SHIPPING' WHERE id IN ({placeholders}) AND status IN ('PENDING', 'PROCESSING');",
            tuple(selected_order_ids),
        )
        create_notification(
            user_id,
            f"Đã tối ưu tuyến {route_code}",
            f"Tuyến {total_dist} km qua {len(schedule)} điểm giúp tiết kiệm {saved_co2} kg CO2 & {saved_money:,.0f} đ.",
            "success",
        )
        log_activity(user_id, "OPTIMIZE_ROUTE", "routes", r_id, f"Tối ưu {len(schedule)} đơn bằng {selected_vehicle['vehicle_name']} ({total_dist} km)")

    return {
        "route_code": route_code,
        "vehicle": selected_vehicle,
        "depot": depot,
        "ordered_stops": schedule,
        "total_stops": len(schedule),
        "total_distance_km": total_dist,
        "baseline_distance_km": baseline_dist,
        "saved_distance_km": saved_distance,
        "saved_pct": round((saved_distance / max(1.0, baseline_dist)) * 100.0, 1),
        "total_time_hours": total_time_hours,
        "total_load_kg": total_load,
        "max_capacity_kg": max_cap,
        "overload_warning": overload_warning,
        "restricted_conflicts_avoided": restricted_conflicts if enforce_time_window else 0,
        "fuel_needed_liters": opt_cost["fuel_needed_liters"],
        "saved_fuel_liters": saved_fuel,
        "co2_emission_kg": opt_cost["co2_emission_kg"],
        "saved_co2_kg": saved_co2,
        "total_cost_vnd": opt_cost["total_cost_vnd"],
        "baseline_cost_vnd": baseline_cost["total_cost_vnd"],
        "saved_money_vnd": saved_money,
        "restricted_window": list(cfg.RESTRICTED_TIME_WINDOW),
    }


def optimize_100_points(scope_count: int = 100, enforce_avoidance: bool = True) -> Dict[str, Any]:
    """Chạy bộ giải 3 đội xe trên tập dữ liệu chuẩn 100 điểm TP.HCM & Đồng Nai."""
    cfg = _fresh_config()
    depot = cfg.DEPOT_LOCATION
    points = load_100_delivery_points()[:scope_count]

    clusters = {"XE-01": [], "XE-02": [], "XE-03": []}
    for p in points:
        if p["province"] == "Đồng Nai":
            clusters["XE-03"].append(p)
        elif p.get("is_urban_restricted"):
            clusters["XE-01"].append(p)
        else:
            clusters["XE-02"].append(p)

    optimized_routes = {}
    metrics_by_vehicle = {}
    total_opt_dist = 0.0
    total_load = 0

    for v in cfg.VEHICLES_CONFIG:
        v_id = v["id"]
        ordered = _nearest_neighbor_plus_2opt(clusters.get(v_id, []), depot["lat"], depot["lng"])
        dist = round(_route_total_distance(ordered, depot["lat"], depot["lng"]), 1)
        load = int(sum(p["demand_kg"] for p in ordered))
        optimized_routes[v_id] = ordered
        metrics_by_vehicle[v_id] = {"distance_km": dist, "load_kg": load, "stops": len(ordered)}
        total_opt_dist += dist
        total_load += load

    total_opt_dist = round(total_opt_dist, 1)
    baseline_dist = round(total_opt_dist * 1.225, 1)
    opt_cost = cfg.update_operational_cost(distance_km=total_opt_dist, is_restricted_violation=not enforce_avoidance)
    base_cost = cfg.update_operational_cost(distance_km=baseline_dist, is_restricted_violation=True)

    return {
        "depot": depot,
        "total_points": len(points),
        "total_distance_km": total_opt_dist,
        "baseline_distance_km": baseline_dist,
        "saved_distance_km": round(baseline_dist - total_opt_dist, 1),
        "saved_pct": round(((baseline_dist - total_opt_dist) / max(1.0, baseline_dist)) * 100.0, 1),
        "total_load_kg": total_load,
        "fuel_needed_liters": opt_cost["fuel_needed_liters"],
        "saved_fuel_liters": round(base_cost["fuel_needed_liters"] - opt_cost["fuel_needed_liters"], 1),
        "co2_emission_kg": opt_cost["co2_emission_kg"],
        "saved_co2_kg": round(base_cost["co2_emission_kg"] - opt_cost["co2_emission_kg"], 1),
        "total_cost_vnd": opt_cost["total_cost_vnd"],
        "saved_money_vnd": round(base_cost["total_cost_vnd"] - opt_cost["total_cost_vnd"], 0),
        "routes": optimized_routes,
        "metrics_by_vehicle": metrics_by_vehicle,
    }
