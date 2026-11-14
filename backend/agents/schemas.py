"""
Pydantic Schemas for EcoLogix AI Stateful Multi-Agent System
Contract định nghĩa chặt chẽ cho ChatRequest, Intent, Candidate, Proposal và ChatResponse.
"""
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    INVENTORY_CHECK = "INVENTORY_CHECK"
    DEMAND_FORECAST = "DEMAND_FORECAST"
    ROUTE_OPTIMIZE = "ROUTE_OPTIMIZE"
    FINANCE_ESG_REPORT = "FINANCE_ESG_REPORT"
    GENERAL_OVERVIEW = "GENERAL_OVERVIEW"


class TraceItem(BaseModel):
    agent: str
    action: str
    status: str = "ok"
    error_code: Optional[str] = None
    timestamp: Optional[str] = None


class IntentPlan(BaseModel):
    intent: IntentType
    confidence: float = 1.0
    extracted_slots: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[int] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[int] = 1


class ProposalDecisionReq(BaseModel):
    action: str = Field(..., description="'approve' hoặc 'reject'")
    expected_version: int = 1
    request_id: Optional[str] = None


class ProposalView(BaseModel):
    id: int
    proposal_code: str
    proposal_type: str
    status: str
    version: int
    summary: str
    candidate_id: Optional[str] = None
    snapshot_ref: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    ok: bool = True
    conversation_id: int
    thread_id: str
    run_id: str
    status: str = "completed"  # 'completed', 'needs_clarification', 'awaiting_approval', 'partial', 'failed'
    reply: str
    missing_slots: List[str] = Field(default_factory=list)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    proposal: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
