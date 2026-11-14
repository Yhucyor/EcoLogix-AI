"""
EcoLogix AI - Multi-Agent AI Assistant & Proposal Decision Routes
Cung cấp API Chat tương tác có State (LangGraph) và quy trình phê duyệt Human-in-the-Loop.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.agents.schemas import ChatRequest, ProposalDecisionReq
from backend.services.ai_service import (
    clear_conversation,
    get_conversation_messages,
    process_agent_query,
)
from backend.services.proposal_service import decide_proposal, get_proposal_by_id

router = APIRouter(prefix="/api/ai", tags=["Multi-Agent AI"])


@router.get("/messages")
def api_ai_messages(user_id: int = 1, current_user: Dict[str, Any] = Depends(get_current_user)):
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else user_id
    return {"messages": get_conversation_messages(user_id=target_uid)}


@router.delete("/messages")
def api_ai_clear(user_id: int = 1, current_user: Dict[str, Any] = Depends(get_current_user)):
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else user_id
    company_id = current_user.get("company_id") or 1
    clear_conversation(user_id=target_uid, company_id=company_id)
    return {"ok": True, "message": "Đã tạo phiên hội thoại mới và xóa sạch ngữ cảnh state cũ!"}


@router.post("/chat")
def api_ai_chat(req: ChatRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else (req.user_id or 1)
    company_id = current_user.get("company_id") or 1
    user_role = current_user.get("role") or "Manager"

    result = process_agent_query(
        user_query=req.query,
        user_id=target_uid,
        conversation_id=req.conversation_id,
        thread_id=req.thread_id,
        company_id=company_id,
        user_role=user_role,
        request_id=req.request_id,
        save_to_db=True,
    )
    return result


@router.get("/proposals/{proposal_id}")
def api_get_proposal(proposal_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    company_id = current_user.get("company_id") or 1
    proposal = get_proposal_by_id(proposal_id, company_id=company_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề xuất hoặc không thuộc quyền sở hữu doanh nghiệp.")
    return {"ok": True, "proposal": proposal}


@router.post("/proposals/{proposal_id}/decision")
def api_decide_proposal(
    proposal_id: int,
    req: ProposalDecisionReq,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    company_id = current_user.get("company_id") or 1
    user_id = current_user["id"]
    user_role = current_user.get("role") or "Auditor"

    ok, msg, res_data = decide_proposal(
        proposal_id=proposal_id,
        action=req.action,
        user_id=user_id,
        user_role=user_role,
        company_id=company_id,
        expected_version=req.expected_version,
        request_id=req.request_id,
    )

    if not ok:
        if "không có quyền" in msg or "Auditor" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return {
        "ok": True,
        "message": msg,
        "result": res_data,
        "proposal": get_proposal_by_id(proposal_id, company_id=company_id),
    }
