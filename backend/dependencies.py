"""
EcoLogix AI - FastAPI Authentication & RBAC Dependencies
Xác thực Bearer token HMAC-SHA256 và kiểm tra phân quyền vai trò (Admin, Manager, Dispatcher, Auditor).
"""
from typing import Dict, Any, Optional
from fastapi import Depends, Header, HTTPException

from backend import config
from backend.services.auth_service import get_user_by_id
from backend.utils.helpers import decode_access_token

DEFAULT_DEMO_USER: Dict[str, Any] = {
    "id": 1,
    "company_id": 1,
    "name": "Nguyễn Văn A",
    "email": "nguyen.van.a@ecologix.vn",
    "role": "Manager",
    "company_name": "EcoLogix Logistics (SME)",
    "has_company": True,
    "permissions": ["ALL", "READ", "WRITE", "OPTIMIZE", "EXPORT", "SETTINGS", "FINANCIAL", "USERS"],
    "is_demo_fallback": True,
}


def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[Dict[str, Any]]:
    """Giải mã Bearer token nếu client gửi lên; báo 401 nếu token hỏng hoặc hết hạn."""
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Định dạng Authorization Bearer không hợp lệ.")
    claims = decode_access_token(parts[1])
    if not claims or not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ.")
    user = get_user_by_id(int(claims["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản không còn tồn tại trong hệ thống.")
    return user


def get_current_user(user: Optional[Dict[str, Any]] = Depends(get_optional_user)) -> Dict[str, Any]:
    """Lấy người dùng hiện tại; khi STRICT_AUTH=True bắt buộc phải đăng nhập."""
    if user is not None:
        return user
    if config.STRICT_AUTH:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng chức năng này.")
    return dict(DEFAULT_DEMO_USER)


def require_roles(*allowed_roles: str):
    """Dependency kiểm tra vai trò hợp lệ cho các API nhạy cảm (RBAC, Live-Code, Settings, Delete)."""
    def _checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        role = current_user.get("role", "")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Vai trò '{role}' không có quyền thực hiện thao tác này (yêu cầu: {', '.join(allowed_roles)}).",
            )
        return current_user
    return _checker

