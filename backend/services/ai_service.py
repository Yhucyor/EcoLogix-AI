"""
EcoLogix AI - Stateful Multi-Agent AI Service (PR 4, 5, 6)
Điều phối đồ thị LangGraph Stateful Multi-Agent System, lưu trữ tin nhắn và quản lý checkpoint bền vững.
"""
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple

from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from backend.agents.graph import build_ecologix_graph
from backend.services.checkpoint_service import DbCheckpointer
from backend.utils.helpers import log_activity


class AgentQueryResult(dict):
    """
    Dict chứa kết quả LangGraph đầy đủ, đồng thời hỗ trợ giải nén tuple 3 phần tử
    (trace, reply, action) cho các hàm gọi cũ hoặc test cũ.
    """
    def __iter__(self):
        return iter((self.get("trace", []), self.get("reply", ""), self.get("action")))


def get_or_create_default_conversation(user_id: int = 1) -> Tuple[int, str]:
    rows = rows_to_dicts(execute_query(
        "SELECT id, title FROM ai_conversations WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
        (user_id,),
    ))
    if rows:
        conv_id = rows[0]["id"]
        thread_id = f"thread_u{user_id}_conv_{conv_id}"
        return conv_id, thread_id
    conv_id = execute_insert(
        "INSERT INTO ai_conversations (user_id, title) VALUES (?, 'Phiên điều hành EcoLogix AI');",
        (user_id,),
    )
    thread_id = f"thread_u{user_id}_conv_{conv_id}"
    return conv_id, thread_id


def get_conversation_messages(conversation_id: Optional[int] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    conv_id, _ = get_or_create_default_conversation(user_id) if not conversation_id else (conversation_id, "")
    rows = rows_to_dicts(execute_query(
        "SELECT id, sender, agent_name, content, reasoning_trace, created_at FROM ai_messages WHERE conversation_id = ? ORDER BY id ASC;",
        (conv_id,),
    ))
    messages = []
    for r in rows:
        parsed_trace = []
        if r.get("reasoning_trace"):
            try:
                parsed_trace = json.loads(r["reasoning_trace"])
            except Exception:
                parsed_trace = []
        messages.append({
            "id": r["id"],
            "sender": r["sender"],
            "agent_name": r.get("agent_name"),
            "content": r["content"],
            "trace": parsed_trace,
            "created_at": r["created_at"],
        })
    return messages


def process_agent_query(
    user_query: str,
    user_id: int = 1,
    conversation_id: Optional[int] = None,
    save_to_db: bool = True,
    company_id: int = 1,
    user_role: str = "Manager",
    thread_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Chạy LangGraph stateful workflow và lưu trữ tin nhắn / checkpoint vào cơ sở dữ liệu."""
    conv_id, default_thread = get_or_create_default_conversation(user_id)
    actual_conv_id = conversation_id or conv_id
    actual_thread = thread_id or f"thread_u{user_id}_conv_{actual_conv_id}"

    # Khởi tạo Checkpointer cho Doanh nghiệp
    checkpointer = DbCheckpointer(company_id=company_id)
    graph = build_ecologix_graph(checkpointer=checkpointer)

    initial_state = {
        "query": user_query.strip(),
        "conversation_id": actual_conv_id,
        "thread_id": actual_thread,
        "company_id": company_id,
        "user_id": user_id,
        "user_role": user_role,
        "request_id": request_id,
    }

    # Thực thi graph
    final_state = graph.invoke(initial_state, config={"configurable": {"thread_id": actual_thread}})

    reply = final_state.get("reply", "")
    trace = final_state.get("trace", [])
    proposal = final_state.get("proposal")
    action_button = final_state.get("action")
    status = final_state.get("status", "completed")
    missing_slots = final_state.get("missing_slots", [])

    if save_to_db and user_query.strip():
        execute_insert(
            "INSERT INTO ai_messages (conversation_id, sender, agent_name, content) VALUES (?, 'user', NULL, ?);",
            (actual_conv_id, user_query.strip()),
        )
        execute_insert(
            "INSERT INTO ai_messages (conversation_id, sender, agent_name, content, reasoning_trace) VALUES (?, 'assistant', 'EcoLogix Multi-Agent System', ?, ?);",
            (actual_conv_id, reply, json.dumps(trace, ensure_ascii=False)),
        )
        log_activity(user_id, "AI_QUERY", "ai_messages", actual_conv_id, f"Hỏi đáp AI: {user_query[:80]}")

    return AgentQueryResult({
        "ok": True,
        "conversation_id": actual_conv_id,
        "thread_id": actual_thread,
        "run_id": final_state.get("run_id", f"run_{uuid.uuid4().hex[:8]}"),
        "status": status,
        "reply": reply,
        "trace": trace,
        "proposal": proposal,
        "action": action_button,
        "missing_slots": missing_slots,
        "confirmed_slots": final_state.get("confirmed_slots", {}),
        "messages": get_conversation_messages(conversation_id=actual_conv_id, user_id=user_id) if save_to_db else [],
    })


def clear_conversation(user_id: int = 1, company_id: int = 1) -> bool:
    """Xóa tin nhắn hội thoại và xóa checkpoint state để bắt đầu phiên mới sạch ngữ cảnh."""
    rows = execute_query("SELECT id FROM ai_conversations WHERE user_id = ?;", (user_id,))
    for r in rows:
        conv_id = r["id"]
        thread_id = f"thread_u{user_id}_conv_{conv_id}"
        # Xóa checkpoint state
        checkpointer = DbCheckpointer(company_id=company_id)
        checkpointer.delete(thread_id)
        execute_update("DELETE FROM ai_messages WHERE conversation_id = ?;", (conv_id,))

    log_activity(user_id, "AI_CLEAR_CHAT", "ai_messages", None, "Làm mới lịch sử và reset state đồ thị AI")
    return True
