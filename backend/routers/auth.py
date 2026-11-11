"""Authentication, Registration, OTP Verify, Password Reset, Session & Onboarding Routes."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.dependencies import get_optional_user, get_current_user
from backend.services.auth_service import (
    authenticate_user,
    register_user,
    resend_verification_otp,
    verify_user_account,
    request_password_reset,
    reset_password,
    complete_onboarding,
    get_onboarding_context,
)
from backend.utils.helpers import log_activity

router = APIRouter(tags=["Auth & Onboarding"])


class LoginReq(BaseModel):
    email: str
    password: str


class RegisterReq(BaseModel):
    name: str
    email: str
    password: str
    phone: str = ""
    role: str = "Manager"
    company_name: str = ""


class VerifyReq(BaseModel):
    email: str
    otp_code: str


class ResendOtpReq(BaseModel):
    email: str


class ForgotReq(BaseModel):
    email: str


class ResetReq(BaseModel):
    email: str
    token: str
    new_password: str


class OnboardingReq(BaseModel):
    company_name: str
    tax_code: str = "0318992211"
    address: str = "Khu Công Nghệ Cao, TP. Thủ Đức"
    city: str = "TP. Hồ Chí Minh"
    industry: str = "Phân phối hàng tiêu dùng (FMCG)"
    size: str = "Doanh nghiệp nhỏ (10 - 50 nhân viên)"
    warehouse_name: str = ""
    warehouse_code: str = ""
    warehouse_address: str = ""
    vehicle_name: str = ""
    vehicle_plate: str = ""
    vehicle_type: str = "Tải nhẹ đô thị"
    fuel_type: str = "Diesel"
    max_load_kg: int = 1500
    fuel_price: int = 23500
    cost_per_km: float = 3800.0
    user_id: int = 1


@router.post("/api/auth/login")
def api_login(req: LoginReq):
    ok, data, msg = authenticate_user(req.email, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return {
        "ok": True,
        "user": data["user"],
        "access_token": data["access_token"],
        "token_type": "bearer",
        "message": msg,
    }


@router.post("/api/auth/register")
def api_register(req: RegisterReq):
    ok, msg, otp, email_sent = register_user(req.name, req.email, req.password, req.phone, req.role, req.company_name)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "demo_otp": otp, "email_sent": email_sent}


@router.post("/api/auth/resend-otp")
def api_resend_otp(req: ResendOtpReq):
    ok, msg, otp, email_sent = resend_verification_otp(req.email)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "demo_otp": otp, "email_sent": email_sent}


@router.post("/api/auth/verify")
def api_verify(req: VerifyReq):
    ok, msg = verify_user_account(req.email, req.otp_code)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/api/auth/forgot")
def api_forgot(req: ForgotReq):
    ok, msg, token, email_sent = request_password_reset(req.email)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"ok": True, "message": msg, "demo_token": token, "email_sent": email_sent}


@router.post("/api/auth/reset")
def api_reset(req: ResetReq):
    ok, msg = reset_password(req.email, req.token, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.get("/api/auth/me")
def api_auth_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"ok": True, "user": user}


@router.post("/api/auth/logout")
def api_logout(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    if user:
        log_activity(user["id"], "USER_LOGOUT", "users", user["id"], f"Đăng xuất phiên ({user['email']})")
    return {"ok": True, "message": "Đã đăng xuất phiên làm việc an toàn."}


@router.get("/api/onboarding/current")
def api_onboarding_current(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    if not user:
        return {"has_company": False, "company": None}
    return get_onboarding_context(user["id"])


@router.post("/api/onboarding")
def api_onboarding(req: OnboardingReq, user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    uid = user["id"] if user else req.user_id
    ok, msg, res = complete_onboarding(req.model_dump(), user_id=uid)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "data": res, "user": res.get("user")}

