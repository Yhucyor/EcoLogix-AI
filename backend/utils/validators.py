"""
EcoLogix AI - Input Validation Utilities
Kiểm tra hợp lệ dữ liệu form và API payload.
"""
import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
        return False, "Email không đúng định dạng (vd: ten@congty.vn)."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    cleaned = re.sub(r"[\s\-\.\+]", "", phone or "")
    if not cleaned.isdigit() or not (9 <= len(cleaned) <= 13):
        return False, "Số điện thoại phải gồm 9–13 chữ số hợp lệ."
    return True, ""


def validate_tax_code(tax_code: str) -> Tuple[bool, str]:
    cleaned = re.sub(r"[\s\-]", "", tax_code or "")
    if not cleaned.isdigit() or len(cleaned) not in (10, 13):
        return False, "Mã số thuế doanh nghiệp Việt Nam phải có 10 hoặc 13 chữ số."
    return True, ""


def validate_non_empty(value: str, field_name: str) -> Tuple[bool, str]:
    if not value or not str(value).strip():
        return False, f"Trường '{field_name}' không được để trống."
    return True, ""


def validate_positive(value: float, field_name: str) -> Tuple[bool, str]:
    try:
        val = float(value)
        if val <= 0:
            return False, f"Giá trị '{field_name}' phải lớn hơn 0."
        return True, ""
    except (TypeError, ValueError):
        return False, f"Giá trị '{field_name}' phải là số hợp lệ."


def validate_password(password: str) -> Tuple[bool, str]:
    if not password or len(password) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    return True, ""

