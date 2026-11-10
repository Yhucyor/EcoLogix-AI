"""Agent 5: Financial Analysis Agent (Costing, ROI & Sensitivity)."""
from backend.services.financial_service import get_financial_overview, get_sensitivity_analysis


def run_finance_agent() -> dict:
    fin = get_financial_overview()
    sens = get_sensitivity_analysis()
    summary = fin["financial_summary"]
    return {
        "agent": "Financial Analysis Agent",
        "trace": f"Tổng hợp {summary['total_orders']} đơn hàng & 5 kỳ chi phí từ SQLite (`expenses`); tính tiết kiệm {summary['cost_saving_pct']}% và ROI {summary['payback_months']} tháng.",
        "financial": fin,
        "sensitivity": sens,
    }

