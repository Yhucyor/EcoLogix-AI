"""
Agent 1: Supervisor Agent (Orchestrator)
Điều phối 5 Agent chuyên trách dựa trên truy vấn tiếng Việt tự nhiên.
Ghi chú minh bạch: Chạy công cụ phân tích Multi-Agent trực tiếp trên dữ liệu SQLite (Demo Mode nội bộ),
hoặc gọi LLM ngoài khi người dùng cấu hình API Key trong Hệ thống.
"""
from typing import Tuple, List, Dict, Any, Optional
import json
import urllib.request

from backend.database.connection import execute_query
from backend.agents.demand_agent import run_demand_agent
from backend.agents.inventory_agent import run_inventory_agent
from backend.agents.route_agent import run_route_agent
from backend.agents.finance_agent import run_finance_agent
from backend.agents.esg_agent import run_esg_agent
from backend import config


def _get_llm_config() -> tuple:
    rows = execute_query("SELECT setting_key, setting_value FROM system_settings WHERE company_id = 1;")
    cfg_map = {r["setting_key"]: r["setting_value"] for r in rows}
    return cfg_map.get("AI_PROVIDER_MODE", "Hybrid-Demo"), (cfg_map.get("LLM_API_KEY") or "").strip()


def _try_external_gemini(api_key: str, query: str, context_summary: str) -> Optional[str]:
    """Tùy chọn gọi Gemini REST API nếu người dùng nhập API key hợp lệ; trả None nếu lỗi."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": (
                        "Bạn là EcoLogix AI - Trợ lý điều hành Chuỗi cung ứng & Logistics xanh bằng tiếng Việt.\n"
                        f"DỮ LIỆU HỆ THỐNG THỰC TẾ (CHỈ DÙNG SỐ LIỆU NÀY, KHÔNG BỊA):\n{context_summary}\n\n"
                        f"CÂU HỎI NGƯỜI DÙNG: {query}"
                    )
                }]
            }]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def orchestrate_query(user_query: str) -> Tuple[List[Dict[str, str]], str, Optional[Dict[str, Any]]]:
    q = (user_query or "").lower()
    trace: List[Dict[str, str]] = []
    action_button: Optional[Dict[str, Any]] = None

    # 1. Điều xe / Lộ trình / Bình Dương / Đồng Nai / Cấm tải
    if any(k in q for k in ["bình dương", "đồng nai", "chọn xe", "dùng xe", "lộ trình", "tuyến", "5 đơn", "cấm tải", "rẻ nhất"]):
        province = "Đồng Nai" if "đồng nai" in q else ("TP.HCM" if "hcm" in q or "nội đô" in q else "Bình Dương")
        trace.append({"agent": "Supervisor Agent", "action": f"Phân loại ý định: Bài toán điều phối xe & tối ưu chi phí tuyến {province}."})

        route_out = run_route_agent(province)
        fin_out = run_finance_agent()
        esg_out = run_esg_agent()
        trace.append({"agent": route_out["agent"], "action": route_out["trace"]})
        trace.append({"agent": fin_out["agent"], "action": fin_out["trace"]})
        trace.append({"agent": esg_out["agent"], "action": esg_out["trace"]})

        best = route_out.get("best")
        if best:
            v = best["vehicle"]
            res = best["result"]
            stops_names = " -> ".join(s["district"] for s in res["ordered_stops"])
            content = (
                f"**Tôi đã phân tích dữ liệu thực tế cho tuyến {province} ({res['total_stops']} đơn hàng, tổng {res['total_load_kg']} kg):**\n"
                f"- **Phương tiện tiết kiệm nhất:** **{v['vehicle_name']}** (Biển số `{v['plate_number']}`, nhiên liệu {v['fuel_type']})\n"
                f"- **Thứ tự lộ trình tối ưu:** Kho Thủ Đức ➔ {stops_names} ➔ Kho (**{res['total_distance_km']} km**, giảm **{res['saved_pct']}%** so với tuyến cũ {res['baseline_distance_km']} km)\n"
                f"- **Chi phí ước tính:** **{res['total_cost_vnd']:,.0f} VNĐ** (Tiết kiệm **{res['saved_money_vnd']:,.0f} VNĐ** với giá xăng `{config.FUEL_PRICE_PER_LITER:,} đ/L`)\n"
                f"- **Giảm phát thải CO₂:** **{res['saved_co2_kg']} kg CO₂** (Tránh hoàn toàn khung giờ cấm tải `{res['restricted_window'][0]}–{res['restricted_window'][1]}`)\n"
            )
            action_button = {"label": "Mở Tối ưu lộ trình & Áp dụng", "target_page": "routing", "action_type": "navigate"}
        else:
            content = "Hiện chưa có đơn hàng chờ điều phối trong cơ sở dữ liệu."

    # 2. Tồn kho / Kho hàng / Thiếu hàng
    elif any(k in q for k in ["kho", "tồn", "còn bao nhiêu", "hết hàng", "thiếu hàng", "sku"]):
        trace.append({"agent": "Supervisor Agent", "action": "Phân loại ý định: Kiểm tra tồn kho thời gian thực & ngưỡng an toàn Safety Stock."})
        inv_out = run_inventory_agent()
        dem_out = run_demand_agent(horizon_days=7)
        trace.append({"agent": inv_out["agent"], "action": inv_out["trace"]})
        trace.append({"agent": dem_out["agent"], "action": dem_out["trace"]})

        low_lines = ""
        if inv_out["low_items"]:
            low_lines = "\n⚠️ **Cảnh báo dưới ngưỡng Safety Stock:**\n" + "\n".join(
                f"- **{r['product_name']}** (`{r['sku']}`) tại *{r['warehouse_name']}*: Còn **{r['quantity']}** {r['unit']} (An toàn: {r['safety_stock']})"
                for r in inv_out["low_items"][:4]
            )
        top_lines = "\n".join(
            f"- **{r['product_name']}** (`{r['sku']}`) tại *{r['warehouse_name']}*: **{r['quantity']}** {r['unit']}"
            for r in inv_out["items"][:4]
        )
        content = (
            f"**Báo cáo tồn kho thực tế trên {len(inv_out['warehouses'])} kho hàng (Hiệu suất kho: {inv_out['metrics']['inventory_efficiency_pct']}%):**\n"
            f"{low_lines if low_lines else top_lines}\n\n"
            "Hệ thống khuyến nghị phát hành Lệnh nhập kho bổ sung cho các SKU chạm ngưỡng an toàn."
        )
        action_button = {"label": "Mở Quản lý Kho & Nhập hàng", "target_page": "inventory", "action_type": "navigate"}

    # 3. Dự báo nhu cầu / Doanh thu / 30 ngày
    elif any(k in q for k in ["dự báo", "nhu cầu", "30 ngày", "doanh thu", "nhập hàng"]):
        trace.append({"agent": "Supervisor Agent", "action": "Kích hoạt Demand Forecasting Agent chạy mô hình LightGBM."})
        dem_out = run_demand_agent(horizon_days=30, product_id=1)
        fin_out = run_finance_agent()
        trace.append({"agent": dem_out["agent"], "action": dem_out["trace"]})
        trace.append({"agent": fin_out["agent"], "action": fin_out["trace"]})

        fc = dem_out["primary_forecast"]
        fin_sum = fin_out["financial"]["financial_summary"]
        content = (
            f"**Kết quả dự báo AI ({fc['model_name']} - Độ chính xác {fc['accuracy_pct']}%):**\n"
            f"- **SKU trọng điểm ({fc['product']['name']}):** Dự báo 30 ngày đạt **{fc['total_forecast']:,} {fc['product']['unit']}** ({fc['growth_pct']:+.1f}%), Safety Stock: **{fc['safety_stock']}**.\n"
            f"- **Tổng cầu nhóm Top 3 SKU (30 ngày):** **{dem_out['top3_total_demand']:,} đơn vị**.\n"
            f"- **Doanh thu đơn hàng hệ thống ghi nhận:** **{fin_sum['total_revenue_vnd']:,.0f} VNĐ** | Tỷ lệ tiết kiệm chi phí: **{fin_sum['cost_saving_pct']}%**.\n"
            f"- **Khuyến nghị nhập kho:** Bổ sung **{fc['suggested_po']:,} {fc['product']['unit']}** cho sản phẩm trọng điểm để tránh đứt gãy."
        )
        action_button = {"label": "Xem biểu đồ Dự báo LightGBM", "target_page": "forecasting", "action_type": "navigate"}

    # 4. ESG / CO2 / Báo cáo tài chính
    elif any(k in q for k in ["co2", "esg", "phát thải", "báo cáo", "tài chính", "xanh", "carbon"]):
        trace.append({"agent": "Supervisor Agent", "action": "Phân công Financial Agent & ESG Carbon Agent tổng hợp báo cáo chuẩn GHG Protocol."})
        esg_out = run_esg_agent()
        fin_out = run_finance_agent()
        trace.append({"agent": esg_out["agent"], "action": esg_out["trace"]})
        trace.append({"agent": fin_out["agent"], "action": fin_out["trace"]})

        esg_s = esg_out["esg"]["esg_summary"]
        fin_s = fin_out["financial"]["financial_summary"]
        content = (
            "**Báo cáo Tài chính & Kiểm toán Phát thải CO₂ (Số liệu thực tế từ SQLite):**\n"
            f"- **Phát thải CO₂ tháng hiện tại:** **{esg_s['total_co2_kg']:,.1f} kg CO₂** (Đã cắt giảm **{esg_s['co2_saved_kg']:,.1f} kg CO₂**, tương đương **-{esg_s['co2_reduction_pct']}%**)\n"
            f"- **Điểm Logistics Xanh (Green Score):** **{esg_s['green_score']}%** (Quy đổi tương đương trồng **{esg_s['trees_equivalent']:,}** cây xanh/năm)\n"
            f"- **Tổng chi phí vận hành tích lũy:** **{fin_s['total_cost_vnd']:,.0f} VNĐ** | ROI hoàn vốn: **{fin_s['payback_months']} tháng**"
        )
        action_button = {"label": "Mở Báo cáo & Xuất PDF/Excel", "target_page": "reports", "action_type": "navigate"}

    # 5. Tổng quan mặc định
    else:
        trace.append({"agent": "Supervisor Agent", "action": f"Tiếp nhận truy vấn tổng quát: '{user_query}'"})
        inv_out = run_inventory_agent()
        fin_out = run_finance_agent()
        esg_out = run_esg_agent()
        trace.append({"agent": inv_out["agent"], "action": inv_out["trace"]})
        trace.append({"agent": fin_out["agent"], "action": fin_out["trace"]})
        trace.append({"agent": esg_out["agent"], "action": esg_out["trace"]})

        fin_s = fin_out["financial"]["financial_summary"]
        esg_s = esg_out["esg"]["esg_summary"]
        content = (
            f"**EcoLogix Multi-Agent System** đã phân tích yêu cầu *\"{user_query}\"*. Tình trạng hệ thống thực tế:\n"
            f"- **Đơn hàng hệ thống:** {fin_s['total_orders']} đơn ({fin_s['shipping_orders']} đang giao) | Hiệu suất kho: **{inv_out['metrics']['inventory_efficiency_pct']}%**\n"
            f"- **Chỉ số xanh & Tài chính:** Tiết kiệm chi phí **{fin_s['cost_saving_pct']}%** | Giảm phát thải **-{esg_s['co2_reduction_pct']}%**\n"
            f"- **Tham số vận hành:** Giá xăng `{config.FUEL_PRICE_PER_LITER:,} đ/L`, Thuế Carbon `{config.CARBON_TAX_RATE:,} đ/kg CO₂`, Cấm tải `{config.RESTRICTED_TIME_WINDOW[0]}–{config.RESTRICTED_TIME_WINDOW[1]}`."
        )

    # Nếu user cấu hình LLM_API_KEY thực tế, tăng cường diễn đạt bằng Gemini dựa trên context số liệu thật
    provider_mode, api_key = _get_llm_config()
    if api_key and provider_mode != "Hybrid-Demo":
        llm_reply = _try_external_gemini(api_key, user_query, content)
        if llm_reply:
            trace.append({"agent": "LLM Synthesizer (Gemini)", "action": "Hoàn thiện câu trả lời bằng mô hình ngôn ngữ lớn gắn ngữ cảnh SQLite."})
            content = llm_reply
    else:
        trace.append({
            "agent": "System Mode",
            "action": "Chạy Engine Multi-Agent + SQLite nội bộ (Demo Mode — chưa cấu hình External LLM API Key)."
        })

    return trace, content, action_button

