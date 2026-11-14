"""
State Definition for EcoLogix AI Multi-Agent System
Quản lý trạng thái đa tầng:
- Qua nhiều lượt: confirmed_slots, thread_id, company_id.
- Theo từng lượt: intent_plan, missing_slots, candidates, evaluations, trace, proposal, status.
"""
from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    conversation_id: int
    thread_id: str
    run_id: str
    turn_id: int
    query: str
    company_id: int
    user_id: int
    user_role: str
    intent_plan: Optional[Dict[str, Any]]
    confirmed_slots: Dict[str, Any]  # e.g. {"sku_code": "SKU-003", "sku_id": 3, "warehouse_name": "Kho Thủ Đức", "horizon_days": 14}
    missing_slots: List[str]
    snapshot_ref: Optional[str]
    candidates: List[Dict[str, Any]]
    evaluations: Dict[str, Dict[str, Any]]  # candidate_id -> {finance: ..., esg: ...}
    proposal: Optional[Dict[str, Any]]
    status: str  # 'needs_clarification' | 'awaiting_approval' | 'partial' | 'completed' | 'failed'
    reply: str
    trace: List[Dict[str, Any]]
    action: Optional[Dict[str, Any]]
