"""Agent 6: ESG & Carbon Analysis Agent (GHG Protocol Scope 1)."""
import importlib
from backend import config
from backend.services.carbon_service import get_esg_overview


def run_esg_agent() -> dict:
    importlib.reload(config)
    esg = get_esg_overview()
    s = esg["esg_summary"]
    return {
        "agent": "ESG & Carbon Analysis Agent",
        "trace": f"Đo lường phát thải từ `routes` & `esg_reports` theo GHG Protocol (thuế Carbon {config.CARBON_TAX_RATE:,} đ/kg CO2): Điểm xanh {s['green_score']}%.",
        "esg": esg,
    }

