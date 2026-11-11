"""Multi-Agent AI Assistant Chat Routes."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.services.ai_service import (
    clear_conversation,
    get_conversation_messages,
    process_agent_query,
)

router = APIRouter(prefix="/api/ai", tags=["Multi-Agent AI"])


class AiChatReq(BaseModel):
    query: str
    user_id: int = 1


@router.get("/messages")
def api_ai_messages(user_id: int = 1, current_user: Dict[str, Any] = Depends(get_current_user)):
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else user_id
    return {"messages": get_conversation_messages(user_id=target_uid)}


@router.delete("/messages")
def api_ai_clear(user_id: int = 1, current_user: Dict[str, Any] = Depends(get_current_user)):
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else user_id
    clear_conversation(user_id=target_uid)
    return {"ok": True, "message": "Đã tạo phiên hội thoại mới!"}


@router.post("/chat")
def api_ai_chat(req: AiChatReq, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    target_uid = current_user["id"] if not current_user.get("is_demo_fallback") else req.user_id
    company_id = current_user.get("company_id") or 1
    trace, reply, action = process_agent_query(req.query, user_id=target_uid, save_to_db=True, company_id=company_id)
    return {
        "ok": True,
        "trace": trace,
        "reply": reply,
        "action": action,
        "messages": get_conversation_messages(user_id=target_uid),
    }

