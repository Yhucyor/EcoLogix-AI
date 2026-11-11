"""
EcoLogix AI - Multi-Agent AI Service
Điều phối 6 Agents trong thư mục `agents/` và lưu trữ hội thoại thật vào `ai_conversations` & `ai_messages`.
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts
from backend.agents.supervisor_agent import orchestrate_query
from backend.utils.helpers import log_activity


def get_or_create_default_conversation(user_id: int = 1) -> int:
    rows = execute_query("SELECT id FROM ai_conversations WHERE user_id = ? ORDER BY id DESC LIMIT 1;", (user_id,))
    if rows:
        return rows[0]["id"]
    return execute_insert("INSERT INTO ai_conversations (user_id, title) VALUES (?, 'Phiên điều hành EcoLogix AI');", (user_id,))


def get_conversation_messages(conversation_id: Optional[int] = None, user_id: int = 1) -> List[Dict[str, Any]]:
    conv_id = conversation_id or get_or_create_default_conversation(user_id)
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
) -> Tuple[List[Dict[str, str]], str, Optional[Dict[str, Any]]]:
    trace, content, action_button = orchestrate_query(user_query, company_id=company_id)

    if save_to_db and user_query.strip():
        conv_id = conversation_id or get_or_create_default_conversation(user_id)
        execute_insert(
            "INSERT INTO ai_messages (conversation_id, sender, agent_name, content) VALUES (?, 'user', NULL, ?);",
            (conv_id, user_query.strip()),
        )
        execute_insert(
            "INSERT INTO ai_messages (conversation_id, sender, agent_name, content, reasoning_trace) VALUES (?, 'assistant', 'Supervisor Agent', ?, ?);",
            (conv_id, content, json.dumps(trace, ensure_ascii=False)),
        )
        log_activity(user_id, "AI_QUERY", "ai_messages", conv_id, f"Hỏi đáp Trợ lý AI: {user_query[:80]}")

    return trace, content, action_button


def clear_conversation(user_id: int = 1) -> bool:
    """Xóa tin nhắn hội thoại AI hiện tại của người dùng để bắt đầu phiên mới."""
    rows = execute_query("SELECT id FROM ai_conversations WHERE user_id = ?;", (user_id,))
    for r in rows:
        execute_update("DELETE FROM ai_messages WHERE conversation_id = ?;", (r["id"],))
    log_activity(user_id, "AI_CLEAR_CHAT", "ai_messages", None, "Làm mới lịch sử trò chuyện Trợ lý AI")
    return True
