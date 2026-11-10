"""
EcoLogix AI - Shared Helper Functions
Password hashing, stateless HMAC-SHA256 access tokens, DB activity logging, notifications & time utilities.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from backend import config
from backend.database.connection import execute_insert


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(payload: Dict[str, Any], expires_hours: int = 24) -> str:
    """Tạo token HMAC-SHA256 (chuẩn 3 phần header.payload.signature)."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    claims = {**payload, "iat": int(time.time()), "exp": int(time.time()) + expires_hours * 3600}
    body = _b64url_encode(json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header}.{body}".encode("ascii")
    sig = hmac.new(config.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Giải mã và xác thực chữ ký + hạn sử dụng token; trả None nếu không hợp lệ."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{body_b64}".encode("ascii")
        expected_sig = hmac.new(config.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(actual_sig, expected_sig):
            return None
        claims = json.loads(_b64url_decode(body_b64).decode("utf-8"))
        if int(claims.get("exp", 0)) < int(time.time()):
            return None
        return claims
    except Exception:
        return None


def hash_password(password: str, salt: bytes = None) -> str:
    """Hash mật khẩu bằng PBKDF2-HMAC-SHA256 kèm salt ngẫu nhiên."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Kiểm tra mật khẩu hợp lệ (hỗ trợ cả PBKDF2 hash và bản demo seed cũ)."""
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2$"):
        try:
            _, salt_hex, dk_hex = stored_hash.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            expected_dk = bytes.fromhex(dk_hex)
            actual_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
            return hmac.compare_digest(actual_dk, expected_dk)
        except Exception:
            return False
    return hmac.compare_digest(password, stored_hash)


def log_activity(user_id: int, action: str, entity: str = None, entity_id: int = None, details: str = ""):
    """Ghi nhật ký thao tác hệ thống vào bảng activity_logs."""
    try:
        return execute_insert(
            """
            INSERT INTO activity_logs (user_id, action, entity, entity_id, details)
            VALUES (?, ?, ?, ?, ?);
            """,
            (user_id, action, entity, entity_id, details),
        )
    except Exception:
        return None


def create_notification(user_id: int, title: str, message: str, notif_type: str = "info"):
    """Tạo thông báo mới lưu trong bảng notifications."""
    try:
        return execute_insert(
            """
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, 0);
            """,
            (user_id, title, message, notif_type),
        )
    except Exception:
        return None


def format_vnd(amount: float) -> str:
    """Định dạng tiền tệ VNĐ."""
    return f"{amount:,.0f} đ"


def time_to_minutes(hhmm: str) -> int:
    """Chuyển chuỗi HH:MM thành số phút kể từ 00:00."""
    try:
        h, m = str(hhmm).strip().split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def windows_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """Kiểm tra hai khung giờ [start_a, end_a] và [start_b, end_b] có giao nhau không."""
    sa, ea = time_to_minutes(start_a), time_to_minutes(end_a)
    sb, eb = time_to_minutes(start_b), time_to_minutes(end_b)
    return max(sa, sb) < min(ea, eb)
