"""
EcoLogix AI - Shared Helper Functions
Password hashing, DB activity logging, automatic notifications, and time utilities.
"""
import hashlib
import os
import hmac
from database.connection import execute_insert


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

