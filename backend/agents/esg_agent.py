"""
Agent 6: ESG & Carbon Analysis Agent (GHG Protocol Scope 1 & Scope 2)
Đo lường lượng phát thải CO2, tỷ lệ cắt giảm và chấm điểm Logistics xanh.
Tách biệt phát thải trực tiếp (Scope 1 Diesel: 2.68 kg CO2/L) và phát thải gián tiếp liên quan điện (Scope 2 EV).
"""
import importlib
from typing import Optional, List, Dict, Any
from backend import config
from backend.services.carbon_service import get_esg_overview


def run_esg_agent(
    company_id: int = 1,
    candidates: Optional[List[Dict[str, Any]]] = None,
    snapshot_ref: Optional[str] = None,
) -> Dict[str, Any]:
    importlib.reload(config)
    esg = get_esg_overview(company_id=company_id)
    summary = esg["esg_summary"]

    candidate_evals = {}
    if candidates:
        for c in candidates:
            c_id = c.get("candidate_id") or str(c.get("vehicle_id"))
            veh = c.get("vehicle") or {}
            is_ev = veh.get("fuel_type") == "Electric"
            co2_kg = float(c.get("co2_emission_kg") or (c.get("result", {}).get("co2_emission_kg") or 0.0))
            saved_co2 = float(c.get("saved_co2_kg") or (c.get("result", {}).get("saved_co2_kg") or 0.0))
            fuel_l = float(c.get("result", {}).get("fuel_needed_liters") or 0.0)

            # Phân tách Scope theo chuẩn GHG Protocol
            scope_type = "Scope 2 (Electricity Grid Factor 0.7221 kg/kWh)" if is_ev else "Scope 1 (Direct Fuel Combustion 2.68 kg/L)"

            candidate_evals[c_id] = {
                "candidate_id": c_id,
                "snapshot_ref": snapshot_ref or c.get("snapshot_ref"),
                "co2_emission_kg": co2_kg,
                "saved_co2_kg": saved_co2,
                "is_electric": is_ev,
                "standard": "GHG Protocol Corporate Standard",
                "scope": scope_type,
                "fuel_or_energy": f"{fuel_l:.2f} kWh" if is_ev else f"{fuel_l:.2f} L",
            }

    trace_msg = (
        f"Kiểm toán phát thải CO₂ theo GHG Protocol cho {len(candidate_evals)} phương án (Snap: {snapshot_ref})."
        if candidate_evals
        else f"Đo lường phát thải từ `routes` & `esg_reports`: Phát thải kỳ {summary['total_co2_kg']} kg, đã giảm {summary['co2_reduction_pct']}%."
    )

    return {
        "agent": "ESG & Carbon Analysis Agent",
        "status": "completed",
        "trace": trace_msg,
        "snapshot_ref": snapshot_ref,
        "candidate_evaluations": candidate_evals,
        "esg": esg,
    }
