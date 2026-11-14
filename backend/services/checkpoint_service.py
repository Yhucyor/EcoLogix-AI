"""
EcoLogix AI - Agent Checkpoint Persistence Service (PR 5)
Lưu trữ và phục hồi trạng thái graph bền vững qua các phiên làm việc và khởi động lại server.
Lưu vào bảng `agent_checkpoints` trong SQLite / TiDB / PostgreSQL.
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from backend.database.connection import execute_query, execute_insert, execute_update, rows_to_dicts


class DbCheckpointer:
    """Checkpointer lưu trạng thái trực tiếp vào bảng agent_checkpoints trong DB."""

    def __init__(self, company_id: int = 1):
        self.company_id = company_id

    def put(self, thread_id: str, state: Dict[str, Any], checkpoint_id: Optional[str] = None) -> str:
        cid = checkpoint_id or f"chk_{uuid.uuid4().hex[:12]}"
        # Chỉ lưu các trường cần thiết phục hồi phiên (tránh object cồng kềnh)
        persisted_state = {
            "conversation_id": state.get("conversation_id"),
            "thread_id": thread_id,
            "turn_id": state.get("turn_id", 1),
            "company_id": state.get("company_id", self.company_id),
            "user_id": state.get("user_id"),
            "user_role": state.get("user_role"),
            "confirmed_slots": state.get("confirmed_slots", {}),
            "snapshot_ref": state.get("snapshot_ref"),
            "proposal": state.get("proposal"),
            "status": state.get("status", "completed"),
            "trace": state.get("trace", [])[-5:],  # Giữ 5 trace gần nhất
        }
        state_str = json.dumps(persisted_state, ensure_ascii=False)
        try:
            execute_insert(
                """
                INSERT INTO agent_checkpoints (thread_id, checkpoint_id, company_id, state_json)
                VALUES (?, ?, ?, ?);
                """,
                (thread_id, cid, self.company_id, state_str),
            )
        except Exception:
            # Nếu trùng checkpoint_id, cập nhật
            execute_update(
                """
                UPDATE agent_checkpoints
                SET state_json = ?, created_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND checkpoint_id = ?;
                """,
                (state_str, thread_id, cid),
            )
        return cid

    def get(self, thread_id: str) -> Optional[Dict[str, Any]]:
        rows = rows_to_dicts(execute_query(
            """
            SELECT state_json FROM agent_checkpoints
            WHERE thread_id = ? AND (company_id = ? OR company_id IS NULL)
            ORDER BY id DESC LIMIT 1;
            """,
            (thread_id, self.company_id),
        ))
        if not rows:
            return None
        try:
            return json.loads(rows[0]["state_json"])
        except Exception:
            return None

    def delete(self, thread_id: str) -> bool:
        execute_update(
            "DELETE FROM agent_checkpoints WHERE thread_id = ? AND (company_id = ? OR company_id IS NULL);",
            (thread_id, self.company_id),
        )
        return True


class InMemorySaver:
    """In-memory checkpointer dùng cho unit test nhanh."""

    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}

    def put(self, thread_id: str, state: Dict[str, Any], checkpoint_id: Optional[str] = None) -> str:
        cid = checkpoint_id or f"chk_{uuid.uuid4().hex[:12]}"
        self.storage[thread_id] = dict(state)
        return cid

    def get(self, thread_id: str) -> Optional[Dict[str, Any]]:
        st = self.storage.get(thread_id)
        return dict(st) if st else None

    def delete(self, thread_id: str) -> bool:
        self.storage.pop(thread_id, None)
        return True


def get_default_checkpointer(company_id: int = 1) -> DbCheckpointer:
    return DbCheckpointer(company_id=company_id)

