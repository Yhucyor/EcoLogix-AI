"""
EcoLogix AI - Stateful Multi-Agent Graph Engine (PR 4 & PR 5)
Cung cấp StateGraph theo đặc tả LangGraph:
- Quản lý State TypedDict đa tầng (confirmed_slots giữ qua các lượt, trace, candidates, proposal).
- Persistent Checkpoint (DbCheckpointer / InMemorySaver).
- Điều phối 6 agents: Intent Parsing -> Slot Resolution -> Routing -> Joint Finance & ESG -> Proposal Creation.
"""
import re
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List

from backend import config
from backend.agents.schemas import IntentType
from backend.agents.state import AgentState
from backend.agents.demand_agent import run_demand_agent
from backend.agents.inventory_agent import run_inventory_agent
from backend.agents.route_agent import run_route_agent
from backend.agents.finance_agent import run_finance_agent
from backend.agents.esg_agent import run_esg_agent
from backend.services.checkpoint_service import DbCheckpointer, InMemorySaver, get_default_checkpointer
from backend.services.proposal_service import create_proposal

START = "__start__"
END = "__end__"


class StateGraph:
    """Built-in pure-Python LangGraph-compatible state graph engine."""

    def __init__(self, state_schema=AgentState):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Tuple[Callable, Dict[str, str]]] = {}

    def add_node(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.nodes[name] = fn

    def add_edge(self, start: str, end: str):
        self.edges[start] = end

    def add_conditional_edges(self, start: str, condition_fn: Callable, mapping: Dict[str, str]):
        self.conditional_edges[start] = (condition_fn, mapping)

    def compile(self, checkpointer=None):
        return CompiledStateGraph(self, checkpointer=checkpointer)


class CompiledStateGraph:
    """Compiled graph sẵn sàng thực thi với thread_id và checkpointer."""

    def __init__(self, graph: StateGraph, checkpointer=None):
        self.graph = graph
        self.checkpointer = checkpointer

    def invoke(self, input_state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cfg = config or {}
        thread_id = cfg.get("configurable", {}).get("thread_id") or input_state.get("thread_id") or str(uuid.uuid4())
        company_id = input_state.get("company_id", 1)

        # 1. Phục hồi state trước đó nếu có checkpointer
        prev_state = {}
        if self.checkpointer and thread_id:
            saved = self.checkpointer.get(thread_id)
            if saved:
                prev_state = saved

        # 2. Hợp nhất state
        current_state: Dict[str, Any] = dict(prev_state)
        current_state.update(input_state)
        current_state["thread_id"] = thread_id
        if "confirmed_slots" not in current_state:
            current_state["confirmed_slots"] = prev_state.get("confirmed_slots", {})

        # 3. Thực thi tuần tự các node
        curr_node = self.graph.edges.get(START, "start_turn")
        visited_count = 0
        max_steps = 25

        while curr_node != END and visited_count < max_steps:
            visited_count += 1
            node_fn = self.graph.nodes.get(curr_node)
            if not node_fn:
                break

            updates = node_fn(current_state)
            if updates and isinstance(updates, dict):
                current_state.update(updates)

            # Kiểm tra xem có conditional edge không
            if curr_node in self.graph.conditional_edges:
                cond_fn, mapping = self.graph.conditional_edges[curr_node]
                branch_key = cond_fn(current_state)
                curr_node = mapping.get(branch_key, END)
            else:
                curr_node = self.graph.edges.get(curr_node, END)

        # 4. Lưu lại checkpoint sau lượt chạy
        if self.checkpointer and thread_id:
            self.checkpointer.put(thread_id, current_state)

        return current_state


# ==================== NODE IMPLEMENTATIONS ====================

def start_turn_node(state: Dict[str, Any]) -> Dict[str, Any]:
    turn_id = state.get("turn_id", 0) + 1
    trace = list(state.get("trace", []))
    q = state.get("query", "").strip()
    trace.append({
        "agent": "Supervisor Orchestrator",
        "action": f"Bắt đầu lượt #{turn_id}: Tiếp nhận truy vấn '{q}'",
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })
    return {
        "turn_id": turn_id,
        "run_id": f"run_{uuid.uuid4().hex[:8]}",
        "missing_slots": [],
        "candidates": [],
        "evaluations": {},
        "proposal": None,
        "trace": trace,
        "status": "in_progress",
    }


def parse_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    q = state.get("query", "").lower()
    trace = list(state.get("trace", []))
    extracted = {}

    # 1. Trích xuất mã SKU (SKU-001, SKU-002, SKU-003, SKU-004, hoặc số)
    sku_match = re.search(r"\b(sku[-\s]?\d+|sản phẩm\s+\d+|hàng\s+\d+)\b", q)
    if sku_match:
        raw_sku = sku_match.group(1).upper().replace(" ", "-")
        if not raw_sku.startswith("SKU-"):
            num_match = re.search(r"\d+", raw_sku)
            raw_sku = f"SKU-{int(num_match.group(0)):03d}" if num_match else raw_sku
        extracted["sku_code"] = raw_sku

    # 2. Trích xuất số ngày dự báo (ví dụ "14 ngày", "7 ngày", "30 ngày")
    horizon_match = re.search(r"(\d+)\s*(ngày|day)", q)
    if horizon_match:
        extracted["horizon_days"] = int(horizon_match.group(1))

    # 3. Trích xuất địa phương / tỉnh thành
    for prov in ["bình dương", "đồng nai", "hà nội", "tp.hcm", "hcm", "sài gòn", "long an", "thủ đức"]:
        if prov in q:
            extracted["province"] = (
                "Bình Dương" if prov == "bình dương"
                else "Đồng Nai" if prov == "đồng nai"
                else "Hà Nội" if prov == "hà nội"
                else "TP.HCM" if prov in ("tp.hcm", "hcm", "sài gòn", "thủ đức")
                else "Long An"
            )
            break

    # 4. Trích xuất số lượng đơn hàng cần giao (ví dụ "12 đơn", "5 đơn", "8 đơn")
    orders_match = re.search(r"(\d+)\s*đơn", q)
    if orders_match:
        extracted["requested_orders"] = int(orders_match.group(1))

    # 5. Trích xuất kho hàng
    if "thủ đức" in q or "kho tổng" in q:
        extracted["warehouse_name"] = "Kho Thủ Đức"
    elif "bình dương" in q and ("kho" in q or "tồn" in q):
        extracted["warehouse_name"] = "Kho Bình Dương"

    # Phân loại Intent chính
    if any(k in q for k in ["lộ trình", "chọn xe", "điều xe", "tuyến", "đơn", "giao", "cấm tải", "so chi phí", "vrp"]):
        intent = IntentType.ROUTE_OPTIMIZE
    elif any(k in q for k in ["dự báo", "tiên lượng", "cầu", "forecast"]):
        intent = IntentType.DEMAND_FORECAST
    elif any(k in q for k in ["tồn kho", "tồn", "còn bao nhiêu", "trong kho", "hết hàng", "thiếu hàng", "safety stock"]):
        intent = IntentType.INVENTORY_CHECK
    elif any(k in q for k in ["esg", "co2", "phát thải", "tài chính", "báo cáo", "roi"]):
        intent = IntentType.FINANCE_ESG_REPORT
    else:
        intent = IntentType.GENERAL_OVERVIEW

    trace.append({
        "agent": "Intent & Slot Parser",
        "action": f"Phân loại Intent: {intent.value} (Slots trích xuất: {extracted})",
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "intent_plan": {
            "intent": intent.value,
            "confidence": 0.95,
            "extracted_slots": extracted,
        },
        "trace": trace,
    }


def resolve_slots_node(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("intent_plan") or {}
    intent = plan.get("intent")
    extracted = plan.get("extracted_slots", {})
    confirmed = dict(state.get("confirmed_slots", {}))
    trace = list(state.get("trace", []))
    q = state.get("query", "").lower()
    missing_slots: List[str] = []

    # Tham chiếu ngữ cảnh câu trước ("SKU đó", "sản phẩm đó", "kho đó", "đơn đó")
    has_anaphora_sku = any(phrase in q for phrase in ["sku đó", "sản phẩm đó", "mặt hàng đó", "sku này", "nó"])
    has_anaphora_wh = any(phrase in q for phrase in ["kho đó", "kho này", "ở đó"])

    # 1. Hợp nhất SKU
    if extracted.get("sku_code"):
        confirmed["sku_code"] = extracted["sku_code"]
    elif has_anaphora_sku and confirmed.get("sku_code"):
        trace.append({
            "agent": "Slot Resolver",
            "action": f"Kế thừa SKU từ ngữ cảnh phiên: {confirmed['sku_code']}",
            "status": "ok",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    # 2. Hợp nhất Kho
    if extracted.get("warehouse_name"):
        confirmed["warehouse_name"] = extracted["warehouse_name"]
    elif has_anaphora_wh and confirmed.get("warehouse_name"):
        trace.append({
            "agent": "Slot Resolver",
            "action": f"Kế thừa Kho từ ngữ cảnh phiên: {confirmed['warehouse_name']}",
            "status": "ok",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    # 3. Hợp nhất Horizon
    if extracted.get("horizon_days"):
        confirmed["horizon_days"] = extracted["horizon_days"]

    # 4. Hợp nhất Tỉnh & Số đơn
    if extracted.get("province"):
        confirmed["province"] = extracted["province"]
    if extracted.get("requested_orders"):
        confirmed["requested_orders"] = extracted["requested_orders"]

    # Kiểm tra thiếu slot bắt buộc theo từng intent
    status = "in_progress"
    reply = ""
    if intent == IntentType.DEMAND_FORECAST.value:
        if not confirmed.get("sku_code"):
            missing_slots.append("sku_code")
            status = "needs_clarification"
            reply = "Bạn muốn dự báo nhu cầu cho sản phẩm (SKU) nào? Vui lòng nêu rõ mã SKU (ví dụ: `SKU-001`, `SKU-003`)."

    return {
        "confirmed_slots": confirmed,
        "missing_slots": missing_slots,
        "status": status,
        "reply": reply if reply else state.get("reply", ""),
        "trace": trace,
    }


def inventory_node(state: Dict[str, Any]) -> Dict[str, Any]:
    company_id = state.get("company_id", 1)
    confirmed = state.get("confirmed_slots", {})
    trace = list(state.get("trace", []))

    sku_code = confirmed.get("sku_code")
    wh_name = confirmed.get("warehouse_name")

    inv_out = run_inventory_agent(
        sku_code=sku_code,
        warehouse_name=wh_name,
        company_id=company_id,
    )

    trace.append({
        "agent": inv_out["agent"],
        "action": inv_out["trace"],
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "inventory_result": inv_out,
        "trace": trace,
    }


def demand_node(state: Dict[str, Any]) -> Dict[str, Any]:
    company_id = state.get("company_id", 1)
    confirmed = state.get("confirmed_slots", {})
    trace = list(state.get("trace", []))

    sku_code = confirmed.get("sku_code")
    horizon = confirmed.get("horizon_days") or 30

    dem_out = run_demand_agent(
        horizon_days=horizon,
        sku_code=sku_code,
        company_id=company_id,
    )

    trace.append({
        "agent": dem_out["agent"],
        "action": dem_out["trace"],
        "status": "ok" if dem_out.get("status") == "completed" else "warning",
        "error_code": dem_out.get("error_code"),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "demand_result": dem_out,
        "trace": trace,
    }


def routing_node(state: Dict[str, Any]) -> Dict[str, Any]:
    company_id = state.get("company_id", 1)
    confirmed = state.get("confirmed_slots", {})
    trace = list(state.get("trace", []))

    prov = confirmed.get("province")
    req_orders = confirmed.get("requested_orders")
    snapshot_ref = f"SNAP-{uuid.uuid4().hex[:8].upper()}"

    route_out = run_route_agent(
        province_filter=prov,
        requested_limit=req_orders,
        company_id=company_id,
        snapshot_ref=snapshot_ref,
    )

    trace.append({
        "agent": route_out["agent"],
        "action": route_out["trace"],
        "status": "ok" if route_out.get("status") == "completed" else "warning",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "snapshot_ref": snapshot_ref,
        "routing_result": route_out,
        "candidates": route_out.get("candidates", []),
        "feasible_candidates": route_out.get("feasible_candidates", []),
        "trace": trace,
    }


def finance_node(state: Dict[str, Any]) -> Dict[str, Any]:
    company_id = state.get("company_id", 1)
    candidates = state.get("candidates", [])
    snap = state.get("snapshot_ref")
    trace = list(state.get("trace", []))

    fin_out = run_finance_agent(
        company_id=company_id,
        candidates=candidates,
        snapshot_ref=snap,
    )

    trace.append({
        "agent": fin_out["agent"],
        "action": fin_out["trace"],
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    evals = dict(state.get("evaluations", {}))
    for c_id, f_eval in fin_out.get("candidate_evaluations", {}).items():
        evals.setdefault(c_id, {})["finance"] = f_eval

    return {
        "finance_result": fin_out,
        "evaluations": evals,
        "trace": trace,
    }


def esg_node(state: Dict[str, Any]) -> Dict[str, Any]:
    company_id = state.get("company_id", 1)
    candidates = state.get("candidates", [])
    snap = state.get("snapshot_ref")
    trace = list(state.get("trace", []))

    esg_out = run_esg_agent(
        company_id=company_id,
        candidates=candidates,
        snapshot_ref=snap,
    )

    trace.append({
        "agent": esg_out["agent"],
        "action": esg_out["trace"],
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    evals = dict(state.get("evaluations", {}))
    for c_id, e_eval in esg_out.get("candidate_evaluations", {}).items():
        evals.setdefault(c_id, {})["esg"] = e_eval

    return {
        "esg_result": esg_out,
        "evaluations": evals,
        "trace": trace,
    }


def compose_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("intent_plan") or {}
    intent = plan.get("intent")
    company_id = state.get("company_id", 1)
    user_id = state.get("user_id", 1)
    thread_id = state.get("thread_id", "")
    run_id = state.get("run_id", "")
    trace = list(state.get("trace", []))

    reply = ""
    proposal = None
    action_button = None
    final_status = "completed"

    if state.get("status") == "needs_clarification":
        return {
            "status": "needs_clarification",
            "reply": state.get("reply", "Vui lòng cung cấp thêm thông tin."),
            "trace": trace,
        }

    # 1. TRẢ LỜI ĐỊNH TUYẾN / ROUTE OPTIMIZE
    if intent == IntentType.ROUTE_OPTIMIZE.value:
        r_res = state.get("routing_result") or {}
        best = r_res.get("best")
        candidates = state.get("candidates") or []
        feasible_count = len(state.get("feasible_candidates") or [])

        if r_res.get("status") == "no_orders_found":
            reply = f"⚠️ {r_res.get('message', 'Không tìm thấy đơn hàng phù hợp.')}"
            final_status = "completed"

        elif not best:
            reply = (
                f"⚠️ **Không có phương án khả thi:** {r_res.get('reason', 'Tất cả các xe đều không đáp ứng ràng buộc tải trọng hoặc lịch trình.')}\n"
                f"- Số xe đánh giá: {len(candidates)} xe\n"
                f"- Số xe khả thi: 0 xe (đều quá tải hoặc vi phạm giờ cấm tải)"
            )
            final_status = "completed"

        else:
            cand_res = best["result"]
            v = best["vehicle"]
            evals = state.get("evaluations", {}).get(best["candidate_id"], {})
            f_eval = evals.get("finance", {})
            e_eval = evals.get("esg", {})

            stops_names = " ➔ ".join(s.get("district", s.get("customer_name", "Điểm giao")) for s in cand_res["ordered_stops"][:6])
            reply = (
                f"**Đã lập và đánh giá {len(candidates)} phương án lộ trình ({feasible_count} khả thi, {len(candidates) - feasible_count} bị loại do quá tải):**\n\n"
                f"🚛 **Phương án tối ưu đã chọn:** **{v['vehicle_name']}** (Biển số `{v['plate_number']}`, Nhiên liệu: **{v['fuel_type']}**)\n"
                f"- **Lộ trình:** Kho ➔ {stops_names} ➔ Kho (**{cand_res['total_distance_km']} km** | Tiết kiệm **{cand_res['saved_distance_km']} km** [-{cand_res['saved_pct']}%] so với FIFO)\n"
                f"- **Chi phí vận hành:** **{cand_res['total_cost_vnd']:,.0f} VNĐ** (Tiết kiệm **{f_eval.get('saved_money_vnd', cand_res['saved_money_vnd']):,.0f} VNĐ** [-{f_eval.get('cost_saving_pct', cand_res['saved_pct'])}%])\n"
                f"- **Phát thải CO₂ ({e_eval.get('scope', 'GHG Protocol')}):** **{cand_res['co2_emission_kg']} kg CO₂** (Cắt giảm **{cand_res['saved_co2_kg']} kg CO₂**)\n"
                f"- **Nguồn cự ly đường:** `{cand_res.get('distance_source', 'estimated').upper()}` | Snapshot: `{best['snapshot_ref']}`\n\n"
                f"👉 *Bản đề xuất đã được tạo bên dưới. Người có thẩm quyền (Admin/Manager) vui lòng xem xét và bấm Duyệt để áp dụng chuyến đi.*"
            )

            # Tạo Proposal để duyệt (Human-in-the-Loop)
            proposal = create_proposal(
                company_id=company_id,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                proposal_type="ROUTE",
                summary=f"Tuyến {cand_res['total_stops']} đơn xe {v['plate_number']} ({cand_res['total_distance_km']} km, tiết kiệm {cand_res['saved_money_vnd']:,.0f}đ)",
                payload={
                    "vehicle_id": v["id"],
                    "vehicle_name": v["vehicle_name"],
                    "plate_number": v["plate_number"],
                    "fuel_type": v["fuel_type"],
                    "order_ids": r_res.get("order_ids", []),
                    "stops": cand_res["ordered_stops"],
                    "total_distance_km": cand_res["total_distance_km"],
                    "baseline_distance_km": cand_res["baseline_distance_km"],
                    "saved_distance_km": cand_res["saved_distance_km"],
                    "total_cost_vnd": cand_res["total_cost_vnd"],
                    "saved_money_vnd": cand_res["saved_money_vnd"],
                    "co2_emission_kg": cand_res["co2_emission_kg"],
                    "saved_co2_kg": cand_res["saved_co2_kg"],
                    "fuel_needed_liters": cand_res["fuel_needed_liters"],
                    "saved_fuel_liters": cand_res["saved_fuel_liters"],
                    "route_code": cand_res["route_code"],
                },
                candidate_id=best["candidate_id"],
                snapshot_ref=best["snapshot_ref"],
            )
            final_status = "awaiting_approval"
            action_button = {
                "label": "Xem bản duyệt lộ trình",
                "target_page": "routing",
                "action_type": "proposal_review",
                "proposal_id": proposal["id"],
            }

    # 2. TRẢ LỜI DỰ BÁO NHU CẦU / DEMAND FORECAST
    elif intent == IntentType.DEMAND_FORECAST.value:
        d_res = state.get("demand_result") or {}
        if d_res.get("status") == "not_found":
            reply = f"⚠️ {d_res.get('message', 'Không tìm thấy sản phẩm.')}"
        elif d_res.get("status") == "insufficient_data":
            reply = f"⚠️ {d_res.get('message', 'Chưa đủ dữ liệu để dự báo.')}"
        else:
            fc = d_res.get("primary_forecast") or {}
            acc_str = f"{fc.get('accuracy_pct')}%" if fc.get("accuracy_pct") is not None else "Đang hiệu chuẩn"
            wape_str = f"{fc.get('wape_pct')}%" if fc.get("wape_pct") is not None else "N/A"
            reply = (
                f"**Kết quả dự báo nhu cầu {d_res['product_name']} (`{d_res['sku']}`) cho kỳ {d_res['horizon_days']} ngày:**\n\n"
                f"- **Mô hình sử dụng:** {fc.get('model_name', 'LightGBM Time-Series')}\n"
                f"- **Độ chính xác kiểm nghiệm:** **{acc_str}** (WAPE: `{wape_str}`)\n"
                f"- **Tổng cầu dự báo {d_res['horizon_days']} ngày tới:** **{fc.get('total_forecast', 0):,} {d_res['unit']}**\n"
                f"- **Mức tồn kho an toàn khuyến nghị (Safety Stock):** **{fc.get('safety_stock', 0):,} {d_res['unit']}**\n"
                f"- **Điểm đặt hàng lại (Reorder Point):** **{fc.get('reorder_point', 0):,} {d_res['unit']}**\n"
            )
            if fc.get("suggested_po", 0) > 0:
                reply += f"\n⚠️ **Khuyến nghị:** Cần phát hành Lệnh nhập kho bổ sung **+{fc['suggested_po']:,} {d_res['unit']}** để tránh nguy cơ đứt gãy tồn kho."
            action_button = {"label": "Xem biểu đồ Dự báo", "target_page": "forecasting", "action_type": "navigate"}

    # 3. TRẢ LỜI TỒN KHO / INVENTORY
    elif intent == IntentType.INVENTORY_CHECK.value:
        inv_res = state.get("inventory_result") or {}
        target_item = inv_res.get("target_item")
        wh = inv_res.get("warehouse")

        if target_item:
            reply = (
                f"**Thông tin tồn kho SKU `{target_item['sku']}` ({target_item['product_name']}):**\n\n"
                f"- **Tồn kho khả dụng (On-Hand):** **{target_item['quantity']} {target_item['unit']}**\n"
                f"- **Kho lưu trữ:** *{target_item['warehouse_name']}*\n"
                f"- **Ngưỡng an toàn (Safety Stock):** **{target_item['safety_stock']} {target_item['unit']}**\n"
                f"- **Điểm đặt hàng lại (Reorder Point):** **{target_item['reorder_point']} {target_item['unit']}**\n"
            )
            if target_item["quantity"] <= target_item["safety_stock"]:
                reply += "\n🔴 **CẢNH BÁO:** Tồn kho hiện tại đang ở mức DƯỚI NGƯỠNG AN TOÀN. Bạn có thể hỏi: *'Dự báo nhu cầu 14 ngày cho SKU này'* để tính toán lượng nhập."
        else:
            items = inv_res.get("items") or []
            top_lines = "\n".join(
                f"- **{it['product_name']}** (`{it['sku']}`) tại *{it['warehouse_name']}*: **{it['quantity']}** {it['unit']} (An toàn: {it['safety_stock']})"
                for it in items[:5]
            )
            reply = (
                f"**Báo cáo tồn kho trên {len(inv_res.get('warehouses', []))} kho hàng:**\n\n"
                f"{top_lines}\n\n"
                f"Bạn có thể hỏi chi tiết về một mã cụ thể, ví dụ: *'Tồn kho của SKU-003'*."
            )
        action_button = {"label": "Mở Quản lý Kho", "target_page": "inventory", "action_type": "navigate"}

    # 4. TRẢ LỜI ESG & TÀI CHÍNH
    elif intent == IntentType.FINANCE_ESG_REPORT.value:
        esg_out = state.get("esg_result") or run_esg_agent(company_id=company_id)
        fin_out = state.get("finance_result") or run_finance_agent(company_id=company_id)
        esg_s = esg_out["esg"]["esg_summary"]
        fin_s = fin_out["financial"]["financial_summary"]
        reply = (
            f"**Báo cáo Quản trị Tài chính & Phát thải ESG ({datetime.now().strftime('%m/%Y')}):**\n\n"
            f"- **Phát thải CO₂ thực tế:** **{esg_s['total_co2_kg']:,.1f} kg CO₂** (Cắt giảm lũy kế: **{esg_s['co2_saved_kg']:,.1f} kg**, tương đương **-{esg_s['co2_reduction_pct']}%**)\n"
            f"- **Điểm Logistics Xanh (Green Score):** **{esg_s['green_score']}%**\n"
            f"- **Tổng doanh thu ghi nhận:** **{fin_s['total_revenue_vnd']:,.0f} VNĐ** (Tổng đơn: {fin_s['total_orders']})\n"
            f"- **Tỷ lệ tiết kiệm chi phí vận hành:** **{fin_s['cost_saving_pct']}%**\n"
            f"- **Giá trị tham chiếu:** Xăng `{config.FUEL_PRICE_PER_LITER:,} đ/L` | Thuế Carbon `{config.CARBON_TAX_RATE:,} đ/kg`"
        )
        action_button = {"label": "Xuất Báo cáo ESG & Tài chính", "target_page": "reports", "action_type": "navigate"}

    # 5. TỔNG QUAN
    else:
        inv_res = state.get("inventory_result") or run_inventory_agent(company_id=company_id)
        fin_out = state.get("finance_result") or run_finance_agent(company_id=company_id)
        fin_s = fin_out["financial"]["financial_summary"]
        reply = (
            f"**Hệ sinh thái EcoLogix Multi-Agent AI sẵn sàng hỗ trợ bạn:**\n\n"
            f"- 📦 **Kho & Tồn kho:** Quản lý {len(inv_res.get('items', []))} mặt hàng SKU, hiệu suất kho {inv_res['metrics']['inventory_efficiency_pct']}%\n"
            f"- 📈 **Dự báo nhu cầu:** Mô hình LightGBM tự động tính Safety Stock & Reorder Point theo kỳ\n"
            f"- 🚚 **Tối ưu Green VRP:** Phân tuyến thông minh tránh giờ cấm tải TP.HCM (6h-9h & 16h-20h), cắt giảm CO₂\n"
            f"- 💰 **Kiểm toán & ESG:** Báo cáo chi phí và phát thải Scope 1/2 chuẩn GHG Protocol\n\n"
            f"💡 *Gợi ý lệnh mẫu:* Bạn hãy thử hỏi: *'Kiểm tra tồn kho của SKU-003'* rồi hỏi tiếp *'Dự báo 14 ngày cho SKU đó'*."
        )

    trace.append({
        "agent": "Response Synthesizer",
        "action": f"Tổng hợp phản hồi hoàn tất. Status: {final_status}. Proposal ID: {proposal['id'] if proposal else 'None'}",
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })

    return {
        "reply": reply,
        "proposal": proposal,
        "action": action_button,
        "status": final_status,
        "trace": trace,
    }


def route_dispatcher_condition(state: Dict[str, Any]) -> str:
    if state.get("status") == "needs_clarification":
        return "compose_response"
    intent = (state.get("intent_plan") or {}).get("intent")
    if intent == IntentType.ROUTE_OPTIMIZE.value:
        return "routing"
    elif intent == IntentType.DEMAND_FORECAST.value:
        return "demand"
    elif intent == IntentType.INVENTORY_CHECK.value:
        return "inventory"
    elif intent == IntentType.FINANCE_ESG_REPORT.value:
        return "finance_esg"
    return "general"


def build_ecologix_graph(checkpointer=None) -> CompiledStateGraph:
    """Xây dựng và biên dịch đồ thị LangGraph Stateful Multi-Agent System."""
    workflow = StateGraph(state_schema=AgentState)

    workflow.add_node("start_turn", start_turn_node)
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("resolve_slots", resolve_slots_node)
    workflow.add_node("inventory", inventory_node)
    workflow.add_node("demand", demand_node)
    workflow.add_node("routing", routing_node)
    workflow.add_node("finance", finance_node)
    workflow.add_node("esg", esg_node)
    workflow.add_node("compose_response", compose_response_node)

    workflow.add_edge(START, "start_turn")
    workflow.add_edge("start_turn", "parse_intent")
    workflow.add_edge("parse_intent", "resolve_slots")

    # Rẽ nhánh điều phối theo Intent
    workflow.add_conditional_edges(
        "resolve_slots",
        route_dispatcher_condition,
        {
            "routing": "routing",
            "demand": "demand",
            "inventory": "inventory",
            "finance_esg": "finance",
            "general": "compose_response",
            "compose_response": "compose_response",
        },
    )

    # Nhánh Routing chạy tiếp Finance & ESG cùng candidate
    workflow.add_edge("routing", "finance")
    workflow.add_edge("finance", "esg")
    workflow.add_edge("esg", "compose_response")

    # Các nhánh khác đi thẳng tới tổng hợp
    workflow.add_edge("inventory", "compose_response")
    workflow.add_edge("demand", "compose_response")
    workflow.add_edge("compose_response", END)

    return workflow.compile(checkpointer=checkpointer)
