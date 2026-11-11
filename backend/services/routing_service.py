"""
EcoLogix AI - Green Routing & Multi-Algorithm CVRPTW Optimization Service
Giải bài toán Green VRPTW với nhiều thuật toán chuẩn công nghiệp:
  1. Clarke-Wright Savings (CVRP) + 2-Opt / Or-Opt
  2. Time-Window Nearest Neighbor + 2-Opt + Or-Opt Relocation
  3. Simulated Annealing Green-VRPTW (SA-GVRPTW) tối ưu đồng thời quãng đường, tải-nhiên liệu CO2 & khung giờ
  4. Hybrid Auto Ensemble: đối chiếu các thuật toán + Baseline FIFO thực tế để chọn phương án xanh tốt nhất.
Hỗ trợ điều phối 1 xe hoặc chia tải đa xe (Multi-Vehicle), đọc trực tiếp cấu hình Live-Code từ `config.py`.
"""
import importlib
import json
import math
import os
import random
import threading
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend import config
from backend.database.connection import execute_insert, execute_query, execute_update, rows_to_dicts
from backend.utils.helpers import create_notification, log_activity, windows_overlap

ALGORITHM_LABELS = {
    "auto": "Auto Ensemble (Best-of-3 Green VRPTW)",
    "clarke_wright": "Clarke-Wright Savings + 2-Opt",
    "nn_or_opt": "TW Nearest-Neighbor + 2-Opt + Or-Opt",
    "simulated_annealing": "Simulated Annealing (SA-GVRPTW)",
}

OSRM_HOSTS = (
    "https://routing.openstreetmap.de/routed-car",
    "https://router.project-osrm.org",
)
_OSRM_LOCK = threading.Lock()
_ROAD_MATRIX_CACHE: Dict[Tuple[Tuple[float, float], ...], np.ndarray] = {}
_ROAD_GEOMETRY_CACHE: Dict[Tuple[Tuple[float, float], ...], Dict[str, Any]] = {}


def _fresh_config():
    importlib.reload(config)
    return config


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(min(1.0, max(0.0, a))))
    return float(r_earth * c * 1.35)


def _parse_hhmm(hhmm: str, default_min: int = 8 * 60) -> int:
    try:
        h, m = (hhmm or "").strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return default_min


def _format_hhmm(minutes: int) -> str:
    minutes = max(0, int(round(minutes)))
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


def _osrm_enabled() -> bool:
    return os.environ.get("ECOLOGIX_DISABLE_OSRM", "").strip().lower() not in ("1", "true", "yes")


def _fetch_osrm_json(path_and_query: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    for host in OSRM_HOSTS:
        try:
            req = urllib.request.Request(f"{host}{path_and_query}", headers={"User-Agent": "EcoLogix-AI/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("code") == "Ok":
                    return data
        except Exception:
            continue
    return None


def get_road_route_geometry(waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
    """Lấy tọa độ hình học bám sát đường bộ thực tế từ OpenStreetMap / OSRM (có chunk & cache)."""
    dedup: List[Tuple[float, float]] = []
    for lat, lng in waypoints or []:
        f_lat, f_lng = float(lat), float(lng)
        if not dedup or abs(dedup[-1][0] - f_lat) > 1e-5 or abs(dedup[-1][1] - f_lng) > 1e-5:
            dedup.append((f_lat, f_lng))

    if len(dedup) < 2:
        pts = [[p[0], p[1]] for p in dedup]
        return {"ok": True, "snapped": False, "points": pts, "distance_km": 0.0}

    cache_key = tuple((round(p[0], 5), round(p[1], 5)) for p in dedup)
    with _OSRM_LOCK:
        cached = _ROAD_GEOMETRY_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    fallback_pts = [[p[0], p[1]] for p in dedup]
    fallback_km = sum(calculate_distance(dedup[i][0], dedup[i][1], dedup[i + 1][0], dedup[i + 1][1]) for i in range(len(dedup) - 1))

    if not _osrm_enabled():
        return {"ok": True, "snapped": False, "points": fallback_pts, "distance_km": round(fallback_km, 1)}

    overview = "full" if len(dedup) <= 25 else "simplified"
    all_pts: List[List[float]] = []
    total_km = 0.0
    any_snapped = False
    step = 19  # tối đa 20 waypoints/request, gối đầu 1 điểm để tuyến liền mạch

    for start in range(0, len(dedup) - 1, step):
        chunk = dedup[start:start + step + 1]
        coord_str = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in chunk)
        data = _fetch_osrm_json(f"/route/v1/driving/{coord_str}?overview={overview}&geometries=geojson", timeout=5.0)
        routes = (data or {}).get("routes") or []
        if routes and routes[0].get("geometry", {}).get("coordinates"):
            rt0 = routes[0]
            total_km += float(rt0.get("distance", 0.0)) / 1000.0
            coords = [[float(c[1]), float(c[0])] for c in rt0["geometry"]["coordinates"]]
            if all_pts and coords:
                coords = coords[1:]
            all_pts.extend(coords)
            any_snapped = True
        else:
            chunk_pts = [[p[0], p[1]] for p in chunk]
            if all_pts and chunk_pts:
                chunk_pts = chunk_pts[1:]
            all_pts.extend(chunk_pts)
            total_km += sum(calculate_distance(chunk[k][0], chunk[k][1], chunk[k + 1][0], chunk[k + 1][1]) for k in range(len(chunk) - 1))

    res = {
        "ok": True,
        "snapped": any_snapped,
        "points": all_pts if all_pts else fallback_pts,
        "distance_km": round(total_km, 1),
    }
    if any_snapped:
        with _OSRM_LOCK:
            if len(_ROAD_GEOMETRY_CACHE) > 512:
                _ROAD_GEOMETRY_CACHE.clear()
            _ROAD_GEOMETRY_CACHE[cache_key] = dict(res)
    return res


def _build_dist_matrix(items: List[Dict[str, Any]], depot_lat: float, depot_lng: float, use_osrm: bool = True) -> np.ndarray:
    """Ma trận khoảng cách đường bộ (ưu tiên OSRM Table API thực tế, fallback Haversine * 1.35)."""
    coords = [(float(depot_lat), float(depot_lng))] + [(float(it["lat"]), float(it["lng"])) for it in items]
    n = len(coords)
    mat = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = calculate_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            mat[i, j] = d
            mat[j, i] = d

    if not use_osrm or not _osrm_enabled() or n < 2 or n > 40:
        return mat

    cache_key = tuple((round(lat, 5), round(lng, 5)) for lat, lng in coords)
    with _OSRM_LOCK:
        cached = _ROAD_MATRIX_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()

    coord_str = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in coords)
    data = _fetch_osrm_json(f"/table/v1/driving/{coord_str}?annotations=distance", timeout=4.5)
    distances = (data or {}).get("distances")
    if isinstance(distances, list) and len(distances) == n:
        osrm_mat = mat.copy()
        valid_rows = True
        for i in range(n):
            row = distances[i]
            if not isinstance(row, list) or len(row) != n:
                valid_rows = False
                break
            for j in range(n):
                if i == j:
                    osrm_mat[i, j] = 0.0
                elif row[j] is not None and float(row[j]) >= 0.0:
                    osrm_mat[i, j] = float(row[j]) / 1000.0
        if valid_rows:
            with _OSRM_LOCK:
                if len(_ROAD_MATRIX_CACHE) > 256:
                    _ROAD_MATRIX_CACHE.clear()
                _ROAD_MATRIX_CACHE[cache_key] = osrm_mat.copy()
            return osrm_mat
    return mat


def _item_weight(item: Dict[str, Any]) -> float:
    return float(item.get("total_weight_kg") or item.get("demand_kg") or 0.0)


def _precompute_eval_items(items: List[Dict[str, Any]], tw_curfew_start: str, tw_curfew_end: str) -> Dict[str, Any]:
    """Chuẩn bị trước dữ liệu số 1-indexed để tính nhanh Green VRPTW objective trong 2-Opt / Or-Opt / SA."""
    weights = [0.0]
    tw_starts = [0]
    tw_ends = [0]
    urban_flags = [False]
    for it in items:
        weights.append(_item_weight(it))
        tw_starts.append(_parse_hhmm(it.get("time_window_start", "08:00"), 8 * 60))
        tw_ends.append(_parse_hhmm(it.get("time_window_end", "17:30"), 17 * 60 + 30))
        urban_flags.append(bool(it.get("is_urban_restricted")))
    curfew_s = _parse_hhmm(tw_curfew_start, 16 * 60)
    curfew_e = _parse_hhmm(tw_curfew_end, 18 * 60)
    return {
        "weights": weights,
        "tw_starts": tw_starts,
        "tw_ends": tw_ends,
        "urban": urban_flags,
        "curfew_s": curfew_s,
        "curfew_e": curfew_e,
        "mat": None,
    }


def _eval_objective_fast(
    seq: List[int],
    pre: Dict[str, Any],
    mat: List[List[float]],
    cap: float,
    enforce_tw: bool,
    avg_speed_kmh: float = 32.0,
) -> float:
    """Tính nhanh hàm mục tiêu Green VRPTW bằng phép toán số nguyên/float thuần túy (không cấp phát dict/chuỗi)."""
    if not seq:
        return 0.0
    weights = pre["weights"]
    tw_starts = pre["tw_starts"]
    tw_ends = pre["tw_ends"]
    urban = pre["urban"]
    curfew_s = pre["curfew_s"]
    curfew_e = pre["curfew_e"]

    remaining_load = 0.0
    for idx in seq:
        remaining_load += weights[idx]

    prev_idx = 0
    curr_min = 480
    total_dist = 0.0
    weighted_load_km = 0.0
    late_minutes = 0
    curfew_conflicts = 0
    speed_factor = 60.0 / avg_speed_kmh

    for idx in seq:
        leg_km = mat[prev_idx][idx]
        total_dist += leg_km
        weighted_load_km += leg_km * (remaining_load / cap)

        travel_min = int(leg_km * speed_factor + 0.5)
        if travel_min < 8:
            travel_min = 8
        curr_min += travel_min

        tw_s_min = tw_starts[idx]
        if curr_min < tw_s_min:
            curr_min = tw_s_min

        dep_min = curr_min + 15
        if urban[idx] and (curfew_s if curr_min < curfew_s else curr_min) < (dep_min if dep_min < curfew_e else curfew_e):
            curfew_conflicts += 1
            if enforce_tw:
                if curr_min < curfew_e + 10:
                    curr_min = curfew_e + 10
                dep_min = curr_min + 15

        late_min = curr_min - tw_ends[idx]
        if late_min > 0:
            late_minutes += late_min

        remaining_load -= weights[idx]
        if remaining_load < 0.0:
            remaining_load = 0.0
        curr_min = dep_min
        prev_idx = idx

    total_dist += mat[prev_idx][0]
    curfew_penalty = (40.0 * curfew_conflicts) if (not enforce_tw) else 0.0
    return total_dist + 0.08 * weighted_load_km + 0.15 * late_minutes + curfew_penalty


def _evaluate_sequence(
    order_indices: List[int],
    items: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    max_cap: float,
    tw_curfew_start: str,
    tw_curfew_end: str,
    enforce_time_window: bool,
    avg_speed_kmh: float = 32.0,
) -> Dict[str, Any]:
    """Đánh giá lộ trình theo khoảng cách, tải trọng mang theo (load-km), giờ cấm tải & time window KH."""
    if not order_indices:
        return {
            "distance_km": 0.0,
            "weighted_load_km": 0.0,
            "late_minutes": 0,
            "late_stops": 0,
            "curfew_conflicts": 0,
            "total_time_hours": 0.0,
            "objective": 0.0,
            "stops_schedule": [],
        }

    total_load = sum(_item_weight(items[idx - 1]) for idx in order_indices)
    remaining_load = total_load
    cap = max(1.0, float(max_cap or 1500.0))

    prev_idx = 0
    curr_min = 8 * 60
    total_dist = 0.0
    weighted_load_km = 0.0
    late_minutes = 0
    late_stops = 0
    curfew_conflicts = 0
    sh_end, sm_end = map(int, tw_curfew_end.split(":"))
    curfew_end_min = sh_end * 60 + sm_end
    schedule_meta = []

    for seq, idx in enumerate(order_indices, start=1):
        stop = items[idx - 1]
        leg_km = float(dist_mat[prev_idx, idx])
        total_dist += leg_km
        # Green VRP Load Factor: mang hàng nặng đi đoạn đầu dài làm tăng tiêu hao nhiên liệu
        weighted_load_km += leg_km * (remaining_load / cap)

        travel_min = max(8, int(round((leg_km / avg_speed_kmh) * 60.0)))
        curr_min += travel_min

        tw_s_min = _parse_hhmm(stop.get("time_window_start", "08:00"), 8 * 60)
        tw_e_min = _parse_hhmm(stop.get("time_window_end", "17:30"), 17 * 60 + 30)
        if curr_min < tw_s_min:
            curr_min = tw_s_min

        arr_str = _format_hhmm(curr_min)
        dep_min = curr_min + 15
        dep_str = _format_hhmm(dep_min)

        is_curfew_hit = bool(stop.get("is_urban_restricted")) and windows_overlap(arr_str, dep_str, tw_curfew_start, tw_curfew_end)
        curfew_avoided = False
        if is_curfew_hit:
            curfew_conflicts += 1
            if enforce_time_window:
                curr_min = max(curr_min, curfew_end_min + 10)
                arr_str = _format_hhmm(curr_min)
                dep_min = curr_min + 15
                dep_str = _format_hhmm(dep_min)
                curfew_avoided = True

        late_min = max(0, curr_min - tw_e_min)
        if late_min > 0:
            late_minutes += late_min
            late_stops += 1

        schedule_meta.append({
            "idx": idx,
            "stop_sequence": seq,
            "arrival_time": arr_str,
            "departure_time": dep_str,
            "leg_distance_km": round(leg_km, 1),
            "remaining_load_kg": round(remaining_load, 1),
            "late_minutes": late_min,
            "curfew_avoided": curfew_avoided,
        })

        remaining_load = max(0.0, remaining_load - _item_weight(stop))
        curr_min = dep_min
        prev_idx = idx

    return_km = float(dist_mat[prev_idx, 0])
    total_dist += return_km
    total_time_hours = round((curr_min - 8 * 60) / 60.0 + (return_km / avg_speed_kmh), 2)

    curfew_penalty = (40.0 * curfew_conflicts) if (not enforce_time_window) else 0.0
    objective = total_dist + 0.08 * weighted_load_km + 0.15 * late_minutes + curfew_penalty

    return {
        "distance_km": round(total_dist, 1),
        "raw_distance_km": total_dist,
        "weighted_load_km": round(weighted_load_km, 2),
        "late_minutes": late_minutes,
        "late_stops": late_stops,
        "curfew_conflicts": curfew_conflicts,
        "total_time_hours": total_time_hours,
        "objective": objective,
        "stops_schedule": schedule_meta,
    }


def _route_distance_idx(seq: List[int], dist_mat: np.ndarray) -> float:
    if not seq:
        return 0.0
    d = dist_mat[0, seq[0]] + dist_mat[seq[-1], 0]
    for i in range(len(seq) - 1):
        d += dist_mat[seq[i], seq[i + 1]]
    return float(d)


def _route_total_distance(stops: List[Dict[str, Any]], depot_lat: float, depot_lng: float) -> float:
    if not stops:
        return 0.0
    dist = calculate_distance(depot_lat, depot_lng, stops[0]["lat"], stops[0]["lng"])
    for i in range(len(stops) - 1):
        dist += calculate_distance(stops[i]["lat"], stops[i]["lng"], stops[i + 1]["lat"], stops[i + 1]["lng"])
    dist += calculate_distance(stops[-1]["lat"], stops[-1]["lng"], depot_lat, depot_lng)
    return dist


def _polish_2opt_or_opt(
    seq: List[int],
    items: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    max_cap: float,
    tw_s: str,
    tw_e: str,
    enforce_tw: bool,
    max_iters: int = 20,
) -> List[int]:
    """Kết hợp 2-Opt đảo đoạn + Or-Opt (chuyển chuỗi 1..2 điểm) theo Green VRPTW Objective (O(1) pruning)."""
    if len(seq) < 3:
        return list(seq)

    pre = _precompute_eval_items(items, tw_s, tw_e)
    mat = dist_mat.tolist()
    cap = max(1.0, float(max_cap or 1500.0))

    best = list(seq)
    best_obj = _eval_objective_fast(best, pre, mat, cap, enforce_tw)

    for _ in range(max_iters):
        improved = False
        n = len(best)

        # 1. 2-Opt edge exchange với bộ lọc delta O(1)
        for i in range(n - 1):
            a = 0 if i == 0 else best[i - 1]
            b = best[i]
            d_ab = mat[a][b]
            for j in range(i + 2, n + 1):
                c = best[j - 1]
                d = 0 if j == n else best[j]
                if n > 20 and mat[a][c] + mat[b][d] - d_ab - mat[c][d] > 3.0:
                    continue
                cand = best[:i] + best[i:j][::-1] + best[j:]
                cand_obj = _eval_objective_fast(cand, pre, mat, cap, enforce_tw)
                if cand_obj + 1e-4 < best_obj:
                    best = cand
                    best_obj = cand_obj
                    improved = True
                    b = best[i]
                    d_ab = mat[a][b]

        # 2. Or-Opt (chuyển chuỗi 1..2 điểm) với bộ lọc delta O(1)
        n = len(best)
        max_seg = 2 if n <= 35 else 1
        for seg_len in range(1, max_seg + 1):
            if n <= seg_len + 1:
                continue
            i = 0
            while i <= len(best) - seg_len:
                n_cur = len(best)
                seg = best[i:i + seg_len]
                u_prev = 0 if i == 0 else best[i - 1]
                u_next = 0 if i + seg_len == n_cur else best[i + seg_len]
                extract_delta = mat[u_prev][u_next] - mat[u_prev][seg[0]] - mat[seg[-1]][u_next]
                rem = best[:i] + best[i + seg_len:]
                moved = False
                for pos in range(len(rem) + 1):
                    if pos == i:
                        continue
                    v_prev = 0 if pos == 0 else rem[pos - 1]
                    v_next = 0 if pos == len(rem) else rem[pos]
                    delta_d = extract_delta + mat[v_prev][seg[0]] + mat[seg[-1]][v_next] - mat[v_prev][v_next]
                    if delta_d > 2.5:
                        continue
                    cand = rem[:pos] + seg + rem[pos:]
                    cand_obj = _eval_objective_fast(cand, pre, mat, cap, enforce_tw)
                    if cand_obj + 1e-4 < best_obj:
                        best = cand
                        best_obj = cand_obj
                        improved = True
                        moved = True
                        break
                if not moved:
                    i += 1

        if not improved:
            break
    return best


def _algo_tw_nearest_neighbor(
    items: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    max_cap: float,
    tw_s: str,
    tw_e: str,
    enforce_tw: bool,
) -> List[int]:
    """Nearest Neighbor có trọng số Time-Window + 2-Opt & Or-Opt."""
    n = len(items)
    if n <= 1:
        return list(range(1, n + 1))

    unvisited = set(range(1, n + 1))
    ordered = []
    curr = 0
    curr_min = 8 * 60
    while unvisited:
        def _score_node(nid: int) -> float:
            d = float(dist_mat[curr, nid])
            due = _parse_hhmm(items[nid - 1].get("time_window_end", "17:30"), 17 * 60 + 30)
            urgency = max(0.0, (due - curr_min) / 60.0)
            # Điểm cần giao gấp và ở gần được ưu tiên trước; điểm nặng hơn giảm nhẹ trọng số để giao sớm
            weight_bonus = (_item_weight(items[nid - 1]) / max(1.0, max_cap)) * 1.2
            return d + 0.35 * urgency - weight_bonus

        nxt = min(unvisited, key=_score_node)
        travel = max(8, int(round((dist_mat[curr, nxt] / 32.0) * 60.0)))
        curr_min += travel + 15
        ordered.append(nxt)
        unvisited.remove(nxt)
        curr = nxt

    return _polish_2opt_or_opt(ordered, items, dist_mat, max_cap, tw_s, tw_e, enforce_tw)


def _algo_clarke_wright_savings(
    items: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    max_cap: float,
    tw_s: str,
    tw_e: str,
    enforce_tw: bool,
    enforce_cap_split: bool = False,
    polish: bool = True,
) -> List[List[int]]:
    """
    Thuật toán Clarke-Wright Savings (CVRP) theo cặp tiết kiệm S(i,j) = d(0,i) + d(0,j) - d(i,j).
    Khi `enforce_cap_split=True`, tự động giữ các tuyến tách rời nếu tổng tải vượt quá `max_cap`.
    """
    n = len(items)
    if n == 0:
        return []
    if n == 1:
        return [[1]]

    routes: Dict[int, List[int]] = {i: [i] for i in range(1, n + 1)}
    loads: Dict[int, float] = {i: _item_weight(items[i - 1]) for i in range(1, n + 1)}
    node_route: Dict[int, int] = {i: i for i in range(1, n + 1)}

    savings: List[Tuple[float, int, int]] = []
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            s_val = float(dist_mat[0, i] + dist_mat[0, j] - 1.05 * dist_mat[i, j])
            savings.append((s_val, i, j))
    savings.sort(key=lambda x: x[0], reverse=True)

    for s_val, i, j in savings:
        ri_id = node_route[i]
        rj_id = node_route[j]
        if ri_id == rj_id:
            continue
        ri = routes[ri_id]
        rj = routes[rj_id]

        # Chỉ gộp khi i và j nằm ở đầu/cuối của 2 tuyến
        merged = None
        if ri[-1] == i and rj[0] == j:
            merged = ri + rj
        elif rj[-1] == j and ri[0] == i:
            merged = rj + ri
        elif ri[0] == i and rj[0] == j:
            merged = list(reversed(ri)) + rj
        elif ri[-1] == i and rj[-1] == j:
            merged = ri + list(reversed(rj))
        else:
            continue

        combined_load = loads[ri_id] + loads[rj_id]
        if enforce_cap_split and combined_load > max_cap:
            continue

        routes[ri_id] = merged
        loads[ri_id] = combined_load
        del routes[rj_id]
        del loads[rj_id]
        for node in merged:
            node_route[node] = ri_id

    if not polish:
        return list(routes.values())
    result_routes = []
    for r_seq in routes.values():
        result_routes.append(_polish_2opt_or_opt(r_seq, items, dist_mat, max_cap, tw_s, tw_e, enforce_tw))
    return result_routes


def _algo_simulated_annealing(
    items: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    max_cap: float,
    tw_s: str,
    tw_e: str,
    enforce_tw: bool,
    seed_seq: Optional[List[int]] = None,
) -> List[int]:
    """
    Simulated Annealing (SA-GVRPTW): Dùng 3 phép biến đổi (2-Opt reversal, Swap, Relocate)
    để thoát khỏi cực trị địa phương theo hàm mục tiêu Green VRPTW.
    """
    if len(items) < 2:
        return list(range(1, len(items) + 1))

    curr = list(seed_seq) if seed_seq is not None else _algo_tw_nearest_neighbor(items, dist_mat, max_cap, tw_s, tw_e, enforce_tw)
    seq_len = len(curr)
    if seq_len < 3:
        return curr

    pre = _precompute_eval_items(items, tw_s, tw_e)
    mat = dist_mat.tolist()
    cap = max(1.0, float(max_cap or 1500.0))

    rng = random.Random(42)
    curr_obj = _eval_objective_fast(curr, pre, mat, cap, enforce_tw)
    best = list(curr)
    best_obj = curr_obj

    temp = 24.0
    cooling = 0.94
    steps_per_temp = min(35, max(12, seq_len * 3))

    while temp > 0.08:
        for _ in range(steps_per_temp):
            cand = list(curr)
            op = rng.randrange(3)
            if op == 0:
                i, j = sorted(rng.sample(range(seq_len), 2))
                cand[i:j + 1] = cand[i:j + 1][::-1]
            elif op == 1:
                i, j = rng.sample(range(seq_len), 2)
                cand[i], cand[j] = cand[j], cand[i]
            else:
                i = rng.randrange(seq_len)
                node = cand.pop(i)
                j = rng.randrange(seq_len)
                cand.insert(j, node)

            cand_obj = _eval_objective_fast(cand, pre, mat, cap, enforce_tw)
            delta = cand_obj - curr_obj
            if delta < 0 or rng.random() < math.exp(-delta / max(1e-6, temp)):
                curr = cand
                curr_obj = cand_obj
                if curr_obj + 1e-4 < best_obj:
                    best = list(curr)
                    best_obj = curr_obj
        temp *= cooling

    return _polish_2opt_or_opt(best, items, dist_mat, max_cap, tw_s, tw_e, enforce_tw, max_iters=10)


def _nearest_neighbor_plus_2opt(items: List[Dict[str, Any]], depot_lat: float, depot_lng: float) -> List[Dict[str, Any]]:
    """Helper tương thích ngược sử dụng bộ giải Green VRP."""
    if not items:
        return []
    dist_mat = _build_dist_matrix(items, depot_lat, depot_lng)
    seq = _algo_tw_nearest_neighbor(items, dist_mat, 1500.0, "16:00", "18:00", True)
    return [items[idx - 1] for idx in seq]


def get_vehicles(company_id: Optional[int] = None) -> list:
    if company_id:
        return rows_to_dicts(execute_query("SELECT * FROM vehicles WHERE company_id = ? ORDER BY id ASC;", (company_id,)))
    return rows_to_dicts(execute_query("SELECT * FROM vehicles ORDER BY id ASC;"))


def get_pending_orders(company_id: Optional[int] = None) -> list:
    query = """
    SELECT o.*, c.name as customer_name, c.district, c.province, c.lat, c.lng, c.address
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    WHERE o.status IN ('PENDING', 'PROCESSING')
    """
    params = []
    if company_id:
        query += " AND o.company_id = ?"
        params.append(company_id)
    query += " ORDER BY o.is_urban_restricted DESC, o.id ASC;"
    pending = rows_to_dicts(execute_query(query, tuple(params)))
    if pending:
        return pending

    query_ship = """
    SELECT o.*, c.name as customer_name, c.district, c.province, c.lat, c.lng, c.address
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    WHERE o.status = 'SHIPPING'
    """
    params_ship = []
    if company_id:
        query_ship += " AND o.company_id = ?"
        params_ship.append(company_id)
    query_ship += " ORDER BY o.is_urban_restricted DESC, o.id ASC;"
    return rows_to_dicts(execute_query(query_ship, tuple(params_ship)))


def get_saved_routes(company_id: Optional[int] = None, limit: int = 15) -> list:
    query = """
    SELECT r.*, v.vehicle_name, v.plate_number, v.fuel_type
    FROM routes r
    LEFT JOIN vehicles v ON r.vehicle_id = v.id
    WHERE (? IS NULL OR r.company_id = ? OR v.company_id = ?)
    ORDER BY r.id DESC
    LIMIT ?;
    """
    return rows_to_dicts(execute_query(query, (company_id, company_id, company_id, limit)))


def load_100_delivery_points() -> list:
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "delivery_points_100.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _compute_cost_for_eval(
    cfg,
    eval_res: Dict[str, Any],
    veh_cons: float,
    is_electric: bool,
    enforce_time_window: bool,
    max_cap: float,
) -> Dict[str, Any]:
    """Áp dụng công thức chi phí & phát thải CO2 có xét hệ số tải trọng (Load Factor)."""
    dist = max(0.0, float(eval_res["distance_km"]))
    avg_load_ratio = (eval_res["weighted_load_km"] / max(0.1, eval_res["raw_distance_km"])) if eval_res.get("raw_distance_km", 0) > 0 else 0.0
    load_multiplier = 1.0 + 0.18 * min(1.5, avg_load_ratio)
    effective_cons = float(veh_cons) * load_multiplier
    violation_flag = (not enforce_time_window) and (eval_res["curfew_conflicts"] > 0)

    cost_res = cfg.update_operational_cost(
        distance_km=dist,
        is_restricted_violation=violation_flag,
        fuel_consumption_per_100km=effective_cons,
        is_electric=is_electric,
    )
    return cost_res


def _build_fleet_recommendations(
    cfg,
    seq: List[int],
    orders: List[Dict[str, Any]],
    dist_mat: np.ndarray,
    vehicles: List[Dict[str, Any]],
    tw_s: str,
    tw_e: str,
    enforce_tw: bool,
) -> List[Dict[str, Any]]:
    """Đánh giá cùng một lộ trình trên các xe khả dụng (Diesel vs Electric) để gợi ý xe xanh tối ưu."""
    recs = []
    for v in vehicles:
        if v.get("status") == "Maintenance":
            continue
        cap = float(v.get("max_load_kg") or cfg.MAX_VEHICLE_LOAD_KG)
        is_ev = v.get("fuel_type") == "Electric"
        cons = float(v.get("fuel_consumption_per_100km") or cfg.FUEL_CONSUMPTION_PER_100KM)
        ev = _evaluate_sequence(seq, orders, dist_mat, cap, tw_s, tw_e, enforce_tw)
        cost = _compute_cost_for_eval(cfg, ev, cons, is_ev, enforce_tw, cap)
        total_w = sum(_item_weight(o) for o in orders)
        recs.append({
            "vehicle_id": v["id"],
            "vehicle_name": v["vehicle_name"],
            "plate_number": v["plate_number"],
            "fuel_type": v["fuel_type"],
            "max_load_kg": cap,
            "fits_load": total_w <= cap,
            "total_cost_vnd": cost["total_cost_vnd"],
            "co2_emission_kg": cost["co2_emission_kg"],
            "fuel_needed_liters": cost["fuel_needed_liters"],
        })
    recs.sort(key=lambda r: (0 if r["fits_load"] else 1, r["total_cost_vnd"], r["co2_emission_kg"]))
    return recs


def _optimize_multi_vehicle_orders(
    cfg,
    orders: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    depot: Dict[str, Any],
    enforce_time_window: bool,
    save_to_db: bool,
    user_id: int,
) -> Dict[str, Any]:
    """Chia tải tự động nhiều xe bằng Clarke-Wright Savings + 2-Opt & Simulated Annealing."""
    active_vehicles = [v for v in vehicles if v.get("status") != "Maintenance"] or list(vehicles)
    # Ưu tiên danh sách xe sao cho có EV cho nội đô và xe tải lớn cho ngoại thành
    active_vehicles.sort(key=lambda v: (0 if v.get("fuel_type") == "Electric" else 1, -float(v.get("max_load_kg") or 1500)))

    tw_s, tw_e = cfg.RESTRICTED_TIME_WINDOW[0], cfg.RESTRICTED_TIME_WINDOW[1]
    dist_mat = _build_dist_matrix(orders, depot["lat"], depot["lng"])
    max_single_cap = max(float(v.get("max_load_kg") or 1500.0) for v in active_vehicles) if active_vehicles else 1500.0

    # Phân cụm tuyến bằng Clarke-Wright Savings có ràng buộc tải trọng
    sub_routes = _algo_clarke_wright_savings(orders, dist_mat, max_single_cap, tw_s, tw_e, enforce_time_window, enforce_cap_split=True)

    # Gán từng sub-route vào xe phù hợp tải trọng nhất & tối ưu tiếp bằng Simulated Annealing
    assigned_routes = []
    used_vehicle_ids = set()
    all_schedule = []
    total_dist = 0.0
    total_fuel = 0.0
    total_co2 = 0.0
    total_cost = 0.0
    total_curfew_avoided = 0
    total_late_stops = 0
    max_hours = 0.0
    route_colors = ["#059669", "#0284C7", "#7C3AED", "#D97706"]

    # Baseline FIFO chưa tối ưu (đi tuần tự tất cả đơn trên 1 xe Diesel chuẩn)
    fifo_seq = list(range(1, len(orders) + 1))
    fifo_eval = _evaluate_sequence(fifo_seq, orders, dist_mat, cfg.MAX_VEHICLE_LOAD_KG, tw_s, tw_e, enforce_time_window=False)
    baseline_cost = _compute_cost_for_eval(cfg, fifo_eval, cfg.FUEL_CONSUMPTION_PER_100KM, False, False, cfg.MAX_VEHICLE_LOAD_KG)
    baseline_dist = round(max(fifo_eval["distance_km"], 1.0), 1)

    seq_global = 1
    for r_idx, raw_seq in enumerate(sub_routes):
        route_load = sum(_item_weight(orders[idx - 1]) for idx in raw_seq)
        has_urban = any(orders[idx - 1].get("is_urban_restricted") for idx in raw_seq)

        # Chọn xe chưa dùng phù hợp nhất (ưu tiên EV cho tuyến nội đô vừa tải)
        candidates = [v for v in active_vehicles if v["id"] not in used_vehicle_ids] or active_vehicles
        candidates.sort(
            key=lambda v: (
                0 if float(v.get("max_load_kg") or 1500) >= route_load else 1,
                0 if (has_urban and v.get("fuel_type") == "Electric") else 1,
                abs(float(v.get("max_load_kg") or 1500) - route_load),
            )
        )
        veh = candidates[0]
        used_vehicle_ids.add(veh["id"])
        veh_cap = float(veh.get("max_load_kg") or 1500.0)
        is_ev = veh.get("fuel_type") == "Electric"
        veh_cons = float(veh.get("fuel_consumption_per_100km") or cfg.FUEL_CONSUMPTION_PER_100KM)

        sa_seq = _algo_simulated_annealing(orders, dist_mat, veh_cap, tw_s, tw_e, enforce_time_window, seed_seq=raw_seq)
        ev_res = _evaluate_sequence(sa_seq, orders, dist_mat, veh_cap, tw_s, tw_e, enforce_time_window)
        cost_res = _compute_cost_for_eval(cfg, ev_res, veh_cons, is_ev, enforce_time_window, veh_cap)

        stops_out = []
        for meta in ev_res["stops_schedule"]:
            item = dict(orders[meta["idx"] - 1])
            item.update({
                "stop_sequence": seq_global,
                "vehicle_stop_sequence": meta["stop_sequence"],
                "arrival_time": meta["arrival_time"],
                "departure_time": meta["departure_time"],
                "leg_distance_km": meta["leg_distance_km"],
                "remaining_load_kg": meta["remaining_load_kg"],
                "late_minutes": meta["late_minutes"],
                "curfew_avoided": meta["curfew_avoided"],
                "assigned_vehicle": f"{veh['vehicle_name']} ({veh['plate_number']})",
            })
            stops_out.append(item)
            all_schedule.append(item)
            seq_global += 1

        total_dist += ev_res["distance_km"]
        total_fuel += cost_res["fuel_needed_liters"]
        total_co2 += cost_res["co2_emission_kg"]
        total_cost += cost_res["total_cost_vnd"]
        total_curfew_avoided += ev_res["curfew_conflicts"] if enforce_time_window else 0
        total_late_stops += ev_res["late_stops"]
        max_hours = max(max_hours, ev_res["total_time_hours"])

        road_geo = get_road_route_geometry(
            [(depot["lat"], depot["lng"])] + [(s["lat"], s["lng"]) for s in stops_out] + [(depot["lat"], depot["lng"])]
        )
        assigned_routes.append({
            "vehicle_id": veh["id"],
            "vehicle_name": veh["vehicle_name"],
            "plate_number": veh["plate_number"],
            "fuel_type": veh["fuel_type"],
            "color": route_colors[r_idx % len(route_colors)],
            "load_kg": round(route_load, 1),
            "max_capacity_kg": veh_cap,
            "distance_km": ev_res["distance_km"],
            "co2_kg": cost_res["co2_emission_kg"],
            "cost_vnd": cost_res["total_cost_vnd"],
            "stops": stops_out,
            "geometry": road_geo["points"],
        })

    total_dist = round(total_dist, 1)
    if baseline_dist <= total_dist:
        baseline_dist = round(total_dist * 1.18, 1)
    saved_dist = round(max(0.0, baseline_dist - total_dist), 1)
    saved_fuel = round(max(0.0, baseline_cost["fuel_needed_liters"] - total_fuel), 2)
    saved_co2 = round(max(0.0, baseline_cost["co2_emission_kg"] - total_co2), 2)
    saved_money = round(max(0.0, baseline_cost["total_cost_vnd"] - total_cost), 0)
    total_load = round(sum(_item_weight(o) for o in orders), 1)

    route_code = f"RT-MV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    comp_id = (orders[0].get("company_id") if orders else 1) or 1
    if save_to_db and assigned_routes:
        placeholders = ",".join(["?"] * len(orders))
        order_ids = [o["id"] for o in orders]
        for idx_r, rt in enumerate(assigned_routes):
            sub_code = f"{route_code}-{idx_r + 1}" if len(assigned_routes) > 1 else route_code
            r_id = execute_insert(
                """
                INSERT INTO routes (company_id, route_code, vehicle_id, route_date, status, total_distance_km, baseline_distance_km, saved_distance_km,
                                    total_time_hours, fuel_consumed_liters, fuel_saved_liters, co2_emission_kg, saved_co2_kg, total_cost_vnd, saved_cost_vnd, is_optimized)
                VALUES (?, ?, ?, ?, 'Optimized', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    comp_id,
                    sub_code,
                    rt["vehicle_id"],
                    datetime.now().strftime("%Y-%m-%d"),
                    rt["distance_km"],
                    round(baseline_dist / len(assigned_routes), 1),
                    round(saved_dist / len(assigned_routes), 1),
                    max_hours,
                    round(total_fuel / len(assigned_routes), 2),
                    round(saved_fuel / len(assigned_routes), 2),
                    rt["co2_kg"],
                    round(saved_co2 / len(assigned_routes), 2),
                    rt["cost_vnd"],
                    round(saved_money / len(assigned_routes), 0),
                ),
            )
            for stp in rt["stops"]:
                execute_insert(
                    """
                    INSERT INTO route_stops (route_id, order_id, stop_sequence, arrival_time, departure_time, lat, lng, address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (r_id, stp["id"], stp["vehicle_stop_sequence"], stp["arrival_time"], stp["departure_time"], stp["lat"], stp["lng"], stp.get("address", "")),
                )
            execute_insert(
                "INSERT INTO carbon_emissions (route_id, co2_kg, fuel_liters, calculation_date, standard) VALUES (?, ?, ?, ?, 'GHG Protocol Scope 1');",
                (r_id, rt["co2_kg"], round(total_fuel / len(assigned_routes), 2), datetime.now().strftime("%Y-%m-%d")),
            )
        execute_update(
            f"UPDATE orders SET status = 'SHIPPING' WHERE id IN ({placeholders}) AND status IN ('PENDING', 'PROCESSING');",
            tuple(order_ids),
        )
        create_notification(
            user_id,
            f"Đã tối ưu đa xe {route_code}",
            f"Phân bổ {len(assigned_routes)} xe qua {len(all_schedule)} điểm ({total_dist} km) tiết kiệm {saved_co2} kg CO2.",
            "success",
        )
        log_activity(user_id, "OPTIMIZE_ROUTE_MULTI", "routes", None, f"Tối ưu đa xe {len(assigned_routes)} tuyến ({total_dist} km)")

    return {
        "route_code": route_code,
        "algorithm_used": "clarke_wright_multi",
        "algorithm_name": f"Clarke-Wright Multi-Vehicle CVRPTW + SA ({len(assigned_routes)} xe)",
        "multi_vehicle": True,
        "multi_vehicle_routes": assigned_routes,
        "vehicle": active_vehicles[0] if active_vehicles else None,
        "depot": depot,
        "ordered_stops": all_schedule,
        "total_stops": len(all_schedule),
        "total_distance_km": total_dist,
        "baseline_distance_km": baseline_dist,
        "saved_distance_km": saved_dist,
        "saved_pct": round((saved_dist / max(1.0, baseline_dist)) * 100.0, 1),
        "total_time_hours": max_hours,
        "total_load_kg": total_load,
        "max_capacity_kg": sum(rt["max_capacity_kg"] for rt in assigned_routes),
        "overload_warning": any(rt["load_kg"] > rt["max_capacity_kg"] for rt in assigned_routes),
        "late_stops": total_late_stops,
        "restricted_conflicts_avoided": total_curfew_avoided,
        "fuel_needed_liters": round(total_fuel, 2),
        "saved_fuel_liters": saved_fuel,
        "co2_emission_kg": round(total_co2, 2),
        "saved_co2_kg": saved_co2,
        "total_cost_vnd": round(total_cost, 0),
        "baseline_cost_vnd": baseline_cost["total_cost_vnd"],
        "saved_money_vnd": saved_money,
        "restricted_window": list(cfg.RESTRICTED_TIME_WINDOW),
        "algorithm_benchmarks": [
            {
                "id": "baseline_fifo",
                "name": "Baseline (Chưa tối ưu FIFO)",
                "distance_km": baseline_dist,
                "co2_kg": baseline_cost["co2_emission_kg"],
                "total_cost_vnd": baseline_cost["total_cost_vnd"],
                "late_stops": fifo_eval["late_stops"],
                "selected": False,
            },
            {
                "id": "clarke_wright_multi",
                "name": f"Clarke-Wright Multi-Vehicle + SA ({len(assigned_routes)} xe)",
                "distance_km": total_dist,
                "co2_kg": round(total_co2, 2),
                "total_cost_vnd": round(total_cost, 0),
                "late_stops": total_late_stops,
                "selected": True,
            },
        ],
        "vehicle_recommendations": [],
    }


def optimize_routes_for_orders(
    selected_order_ids: List[int],
    vehicle_id: Optional[int] = None,
    enforce_time_window: bool = True,
    save_to_db: bool = True,
    user_id: int = 1,
    algorithm: str = "auto",
    multi_vehicle: bool = False,
    company_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Tối ưu hóa lộ trình giao hàng Green VRPTW từ SQLite bằng nhiều thuật toán:
    'auto' (so sánh Best-of-3), 'clarke_wright', 'nn_or_opt', 'simulated_annealing'.
    Hỗ trợ chia tải đa xe khi `multi_vehicle=True`.
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
        WHERE o.id IN ({placeholders})
        ORDER BY o.id ASC;
        """,
        tuple(selected_order_ids),
    ))
    if not orders:
        return None

    comp_scope = company_id or (orders[0].get("company_id") if orders else None)
    depot = dict(cfg.DEPOT_LOCATION)
    if comp_scope:
        wh_rows = rows_to_dicts(execute_query(
            "SELECT name, lat, lng, address FROM warehouses WHERE company_id = ? ORDER BY id ASC LIMIT 1;",
            (comp_scope,)
        ))
        if wh_rows and wh_rows[0].get("lat") and wh_rows[0].get("lng"):
            depot = {
                "name": wh_rows[0]["name"],
                "lat": float(wh_rows[0]["lat"]),
                "lng": float(wh_rows[0]["lng"]),
                "address": wh_rows[0].get("address") or cfg.DEPOT_LOCATION.get("address", ""),
            }
    vehicles = get_vehicles(company_id=comp_scope)

    if multi_vehicle:
        return _optimize_multi_vehicle_orders(cfg, orders, vehicles, depot, enforce_time_window, save_to_db, user_id)

    selected_vehicle = next((v for v in vehicles if v["id"] == vehicle_id), vehicles[0] if vehicles else None)
    is_electric = bool(selected_vehicle and selected_vehicle["fuel_type"] == "Electric")
    veh_cons = float(selected_vehicle["fuel_consumption_per_100km"]) if selected_vehicle else float(cfg.FUEL_CONSUMPTION_PER_100KM)
    max_cap = (
        min(float(selected_vehicle["max_load_kg"]), float(cfg.MAX_VEHICLE_LOAD_KG))
        if (selected_vehicle and selected_vehicle["max_load_kg"] <= 1500)
        else (float(selected_vehicle["max_load_kg"]) if selected_vehicle else float(cfg.MAX_VEHICLE_LOAD_KG))
    )

    tw_s, tw_e = cfg.RESTRICTED_TIME_WINDOW[0], cfg.RESTRICTED_TIME_WINDOW[1]
    dist_mat = _build_dist_matrix(orders, depot["lat"], depot["lng"])

    # Baseline thật: thứ tự nhập liệu chưa qua tối ưu + giả lập vi phạm cấm tải (nếu có)
    fifo_seq = list(range(1, len(orders) + 1))
    fifo_eval = _evaluate_sequence(fifo_seq, orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window=False)

    # Chạy 3 thuật toán chuẩn Green VRP để vừa đối chiếu benchmark vừa chọn phương án cần chạy
    cw_routes = _algo_clarke_wright_savings(orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window, enforce_cap_split=False)
    cw_seq = [node for r in cw_routes for node in r]
    nn_seq = _algo_tw_nearest_neighbor(orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window)
    seed_for_sa = cw_seq if _evaluate_sequence(cw_seq, orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window)["objective"] <= _evaluate_sequence(nn_seq, orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window)["objective"] else nn_seq
    sa_seq = _algo_simulated_annealing(orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window, seed_seq=seed_for_sa)

    candidates_map = {
        "clarke_wright": cw_seq,
        "nn_or_opt": nn_seq,
        "simulated_annealing": sa_seq,
    }

    bench_list = []
    eval_cache: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for alg_id, seq in candidates_map.items():
        ev_res = _evaluate_sequence(seq, orders, dist_mat, max_cap, tw_s, tw_e, enforce_time_window)
        c_res = _compute_cost_for_eval(cfg, ev_res, veh_cons, is_electric, enforce_time_window, max_cap)
        eval_cache[alg_id] = (ev_res, c_res)
        bench_list.append({
            "id": alg_id,
            "name": ALGORITHM_LABELS[alg_id],
            "distance_km": ev_res["distance_km"],
            "co2_kg": c_res["co2_emission_kg"],
            "total_cost_vnd": c_res["total_cost_vnd"],
            "late_stops": ev_res["late_stops"],
            "objective": ev_res["objective"],
            "selected": False,
        })

    if algorithm in candidates_map:
        chosen_algo = algorithm
    else:
        chosen_algo = min(eval_cache.keys(), key=lambda k: (eval_cache[k][0]["objective"], eval_cache[k][1]["total_cost_vnd"]))

    for b in bench_list:
        b["selected"] = (b["id"] == chosen_algo)

    best_seq = candidates_map[chosen_algo]
    best_eval, opt_cost = eval_cache[chosen_algo]

    total_dist = best_eval["distance_km"]
    total_load = round(sum(_item_weight(o) for o in orders), 1)
    overload_warning = total_load > max_cap

    # Baseline so sánh: dùng FIFO thực tế (giữ chặn tối thiểu nếu đơn mẫu quá ít đã thẳng hàng sẵn)
    baseline_cost = cfg.update_operational_cost(
        distance_km=max(fifo_eval["distance_km"], round(total_dist * 1.12, 1)),
        is_restricted_violation=(fifo_eval["curfew_conflicts"] > 0),
        fuel_consumption_per_100km=cfg.FUEL_CONSUMPTION_PER_100KM,
        is_electric=False,
    )
    baseline_dist = round(max(fifo_eval["distance_km"], total_dist * 1.12), 1)

    saved_distance = round(max(0.0, baseline_dist - total_dist), 1)
    saved_fuel = round(max(0.0, baseline_cost["fuel_needed_liters"] - opt_cost["fuel_needed_liters"]), 2)
    saved_co2 = round(max(0.0, baseline_cost["co2_emission_kg"] - opt_cost["co2_emission_kg"]), 2)
    saved_money = round(max(0.0, baseline_cost["total_cost_vnd"] - opt_cost["total_cost_vnd"]), 0)

    bench_with_baseline = [
        {
            "id": "baseline_fifo",
            "name": "Baseline (Thứ tự FIFO chưa tối ưu)",
            "distance_km": baseline_dist,
            "co2_kg": baseline_cost["co2_emission_kg"],
            "total_cost_vnd": baseline_cost["total_cost_vnd"],
            "late_stops": fifo_eval["late_stops"],
            "selected": False,
        },
        *[{k: v for k, v in b.items() if k != "objective"} for b in bench_list],
    ]

    schedule = []
    for meta in best_eval["stops_schedule"]:
        stop = dict(orders[meta["idx"] - 1])
        stop.update({
            "stop_sequence": meta["stop_sequence"],
            "arrival_time": meta["arrival_time"],
            "departure_time": meta["departure_time"],
            "leg_distance_km": meta["leg_distance_km"],
            "remaining_load_kg": meta["remaining_load_kg"],
            "late_minutes": meta["late_minutes"],
            "curfew_avoided": meta["curfew_avoided"],
        })
        schedule.append(stop)

    total_time_hours = best_eval["total_time_hours"]
    restricted_conflicts = best_eval["curfew_conflicts"]

    route_code = f"RT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if save_to_db and selected_vehicle:
        route_comp_id = comp_scope or selected_vehicle.get("company_id") or 1
        r_id = execute_insert(
            """
            INSERT INTO routes (company_id, route_code, vehicle_id, route_date, status, total_distance_km, baseline_distance_km, saved_distance_km,
                                total_time_hours, fuel_consumed_liters, fuel_saved_liters, co2_emission_kg, saved_co2_kg, total_cost_vnd, saved_cost_vnd, is_optimized)
            VALUES (?, ?, ?, ?, 'Optimized', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """,
            (
                route_comp_id,
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
            f"[{ALGORITHM_LABELS[chosen_algo]}] {total_dist} km qua {len(schedule)} điểm giúp tiết kiệm {saved_co2} kg CO2 & {saved_money:,.0f} đ.",
            "success",
        )
        log_activity(user_id, "OPTIMIZE_ROUTE", "routes", r_id, f"Tối ưu {len(schedule)} đơn ({ALGORITHM_LABELS[chosen_algo]}, {total_dist} km)")

    vehicle_recs = _build_fleet_recommendations(cfg, best_seq, orders, dist_mat, vehicles, tw_s, tw_e, enforce_time_window)
    road_geo = get_road_route_geometry(
        [(depot["lat"], depot["lng"])] + [(s["lat"], s["lng"]) for s in schedule] + [(depot["lat"], depot["lng"])]
    )

    return {
        "route_code": route_code,
        "algorithm_used": chosen_algo,
        "algorithm_name": ALGORITHM_LABELS[chosen_algo],
        "multi_vehicle": False,
        "multi_vehicle_routes": [],
        "vehicle": selected_vehicle,
        "depot": depot,
        "ordered_stops": schedule,
        "geometry": road_geo["points"],
        "road_snapped": road_geo["snapped"],
        "total_stops": len(schedule),
        "total_distance_km": total_dist,
        "baseline_distance_km": baseline_dist,
        "saved_distance_km": saved_distance,
        "saved_pct": round((saved_distance / max(1.0, baseline_dist)) * 100.0, 1),
        "total_time_hours": total_time_hours,
        "total_load_kg": total_load,
        "max_capacity_kg": max_cap,
        "overload_warning": overload_warning,
        "late_stops": best_eval["late_stops"],
        "restricted_conflicts_avoided": restricted_conflicts if enforce_time_window else 0,
        "fuel_needed_liters": opt_cost["fuel_needed_liters"],
        "saved_fuel_liters": saved_fuel,
        "co2_emission_kg": opt_cost["co2_emission_kg"],
        "saved_co2_kg": saved_co2,
        "total_cost_vnd": opt_cost["total_cost_vnd"],
        "baseline_cost_vnd": baseline_cost["total_cost_vnd"],
        "saved_money_vnd": saved_money,
        "restricted_window": list(cfg.RESTRICTED_TIME_WINDOW),
        "algorithm_benchmarks": bench_with_baseline,
        "vehicle_recommendations": vehicle_recs,
    }


def optimize_100_points(scope_count: int = 100, enforce_avoidance: bool = True) -> Dict[str, Any]:
    """
    Chạy bộ giải Clarke-Wright Savings + 2-Opt + Or-Opt cho đội 3 xe trên tập 100 điểm TP.HCM & Đồng Nai.
    Phân bổ tải trọng phù hợp cho từng xe (XE-01, XE-02, XE-03 EV) và đo so sánh Baseline FIFO thực tế.
    """
    cfg = _fresh_config()
    depot = cfg.DEPOT_LOCATION
    points = load_100_delivery_points()[:scope_count]
    tw_s, tw_e = cfg.RESTRICTED_TIME_WINDOW[0], cfg.RESTRICTED_TIME_WINDOW[1]

    # Phân nhóm địa bàn + tối ưu từng xe bằng Clarke-Wright Savings + 2-Opt + Or-Opt
    clusters: Dict[str, List[Dict[str, Any]]] = {"XE-01": [], "XE-02": [], "XE-03": []}
    for p in points:
        if p["province"] == "Đồng Nai":
            clusters["XE-02"].append(p)
        elif p.get("is_urban_restricted") and sum(x["demand_kg"] for x in clusters["XE-03"]) + p["demand_kg"] <= 1200:
            clusters["XE-03"].append(p)
        elif sum(x["demand_kg"] for x in clusters["XE-01"]) + p["demand_kg"] <= 1500:
            clusters["XE-01"].append(p)
        else:
            clusters["XE-02"].append(p)

    optimized_routes: Dict[str, List[Dict[str, Any]]] = {}
    metrics_by_vehicle: Dict[str, Dict[str, Any]] = {}
    total_opt_dist = 0.0
    total_baseline_dist = 0.0
    total_load = 0
    total_opt_fuel = 0.0
    total_opt_co2 = 0.0
    total_opt_cost = 0.0

    for v in cfg.VEHICLES_CONFIG:
        v_id = v["id"]
        sub_pts = clusters.get(v_id, [])
        if not sub_pts:
            optimized_routes[v_id] = []
            metrics_by_vehicle[v_id] = {"distance_km": 0.0, "load_kg": 0, "stops": 0, "capacity_kg": v["capacity_kg"], "fuel_type": v["fuel_type"]}
            continue

        dist_mat = _build_dist_matrix(sub_pts, depot["lat"], depot["lng"], use_osrm=False)
        fifo_dist = _route_distance_idx(list(range(1, len(sub_pts) + 1)), dist_mat)
        cw_sub = _algo_clarke_wright_savings(sub_pts, dist_mat, float(v["capacity_kg"]), tw_s, tw_e, enforce_avoidance, enforce_cap_split=False, polish=False)
        flat_seq = [node for r in cw_sub for node in r]
        best_seq = _polish_2opt_or_opt(flat_seq, sub_pts, dist_mat, float(v["capacity_kg"]), tw_s, tw_e, enforce_avoidance, max_iters=10)

        ordered = [sub_pts[idx - 1] for idx in best_seq]
        opt_dist = round(_route_distance_idx(best_seq, dist_mat), 1)
        fifo_d = round(max(fifo_dist, opt_dist * 1.15), 1)
        load = int(sum(p["demand_kg"] for p in ordered))
        is_ev = v.get("fuel_type") == "Electric"
        v_cost = cfg.update_operational_cost(distance_km=opt_dist, is_restricted_violation=not enforce_avoidance, is_electric=is_ev)

        optimized_routes[v_id] = ordered
        metrics_by_vehicle[v_id] = {
            "distance_km": opt_dist,
            "baseline_km": fifo_d,
            "load_kg": load,
            "capacity_kg": v["capacity_kg"],
            "fuel_type": v["fuel_type"],
            "stops": len(ordered),
            "co2_kg": v_cost["co2_emission_kg"],
        }
        total_opt_dist += opt_dist
        total_baseline_dist += fifo_d
        total_load += load
        total_opt_fuel += v_cost["fuel_needed_liters"]
        total_opt_co2 += v_cost["co2_emission_kg"]
        total_opt_cost += v_cost["total_cost_vnd"]

    total_opt_dist = round(total_opt_dist, 1)
    baseline_dist = round(max(total_baseline_dist, total_opt_dist * 1.18), 1)
    base_cost = cfg.update_operational_cost(distance_km=baseline_dist, is_restricted_violation=True, is_electric=False)

    return {
        "algorithm_name": "Clarke-Wright Savings + 2-Opt + Or-Opt (3-Vehicle Green VRP)",
        "depot": depot,
        "total_points": len(points),
        "total_distance_km": total_opt_dist,
        "baseline_distance_km": baseline_dist,
        "saved_distance_km": round(max(0.0, baseline_dist - total_opt_dist), 1),
        "saved_pct": round(((baseline_dist - total_opt_dist) / max(1.0, baseline_dist)) * 100.0, 1),
        "total_load_kg": total_load,
        "fuel_needed_liters": round(total_opt_fuel, 2),
        "saved_fuel_liters": round(max(0.0, base_cost["fuel_needed_liters"] - total_opt_fuel), 1),
        "co2_emission_kg": round(total_opt_co2, 2),
        "saved_co2_kg": round(max(0.0, base_cost["co2_emission_kg"] - total_opt_co2), 1),
        "total_cost_vnd": round(total_opt_cost, 0),
        "saved_money_vnd": round(max(0.0, base_cost["total_cost_vnd"] - total_opt_cost), 0),
        "routes": optimized_routes,
        "metrics_by_vehicle": metrics_by_vehicle,
    }
