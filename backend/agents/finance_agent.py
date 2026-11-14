"""
Agent 5: Financial Analysis Agent (Costing, ROI & Sensitivity)
Tính toán chi phí vận hành, tỷ lệ tiết kiệm so với baseline FIFO và độ nhạy giá nhiên liệu/thuế Carbon.
Đảm bảo đánh giá đúng candidate_id và snapshot_ref; baseline trùng phương án thì tiết kiệm = 0.
"""
from typing import Optional, List, Dict, Any
from backend.services.financial_service import get_financial_overview, get_sensitivity_analysis


def run_finance_agent(
    company_id: int = 1,
    candidates: Optional[List[Dict[str, Any]]] = None,
    snapshot_ref: Optional[str] = None,
) -> Dict[str, Any]:
    fin = get_financial_overview(company_id=company_id)
    sens = get_sensitivity_analysis()
    summary = fin["financial_summary"]

    candidate_evals = {}
    if candidates:
        for c in candidates:
            c_id = c.get("candidate_id") or str(c.get("vehicle_id"))
            base_c = float(c.get("baseline_cost_vnd") or (c.get("result", {}).get("baseline_cost_vnd") or 0.0))
            tot_c = float(c.get("total_cost_vnd") or (c.get("result", {}).get("total_cost_vnd") or 0.0))
            saved_m = float(c.get("saved_money_vnd") or (c.get("result", {}).get("saved_money_vnd") or 0.0))
            savings_pct = round(((base_c - tot_c) / base_c) * 100.0, 1) if base_c > 0 else 0.0

            candidate_evals[c_id] = {
                "candidate_id": c_id,
                "snapshot_ref": snapshot_ref or c.get("snapshot_ref"),
                "total_cost_vnd": tot_c,
                "baseline_cost_vnd": base_c,
                "saved_money_vnd": saved_m,
                "cost_saving_pct": savings_pct,
                "fuel_needed_liters": c.get("result", {}).get("fuel_needed_liters", 0.0),
            }

    trace_msg = (
        f"Đánh giá tài chính cho {len(candidate_evals)} phương án lộ trình (Snap: {snapshot_ref})."
        if candidate_evals
        else f"Tổng hợp {summary['total_orders']} đơn hàng & chi phí vận hành; tiết kiệm lũy kế {summary['cost_saving_pct']}%."
    )

    return {
        "agent": "Financial Analysis Agent",
        "status": "completed",
        "trace": trace_msg,
        "snapshot_ref": snapshot_ref,
        "candidate_evaluations": candidate_evals,
        "financial": fin,
        "sensitivity": sens,
    }
