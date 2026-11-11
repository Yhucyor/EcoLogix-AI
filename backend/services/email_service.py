"""
EcoLogix AI - Transactional & Consultation Email Service
Gửi email thực tế qua Gmail/SMTP (nếu cấu hình SMTP_USER / SMTP_PASSWORD)
cho các luồng: Đăng ký OTP, Quên mật khẩu, Đặt lịch tư vấn & FAQ.
"""
from datetime import datetime
from email.message import EmailMessage
from html import escape
import os
import smtplib
from typing import Any, Dict
from urllib.parse import quote

from backend import config


def _clean_header_value(val: str) -> str:
    """Loại bỏ ký tự xuống dòng để tránh SMTP header injection."""
    return " ".join((val or "").replace("\r", " ").replace("\n", " ").split()).strip()


def get_contact_recipient() -> str:
    return (
        os.environ.get("ECOLOGIX_CONTACT_EMAIL")
        or getattr(config, "CONTACT_RECIPIENT_EMAIL", "geroolyhuicy@gmail.com")
        or "geroolyhuicy@gmail.com"
    ).strip()


def build_mailto_url(recipient: str, subject: str, body: str) -> str:
    return f"mailto:{recipient}?subject={quote(subject)}&body={quote(body)}"


def build_gmail_compose_url(recipient: str, subject: str, body: str) -> str:
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={quote(recipient)}&su={quote(subject)}&body={quote(body)}"
    )


def _get_smtp_settings() -> Dict[str, Any]:
    smtp_host = (os.environ["SMTP_HOST"] if "SMTP_HOST" in os.environ else getattr(config, "SMTP_HOST", "smtp.gmail.com")).strip()
    smtp_port = int(os.environ["SMTP_PORT"] if "SMTP_PORT" in os.environ else getattr(config, "SMTP_PORT", 587))
    smtp_user = (os.environ["SMTP_USER"] if "SMTP_USER" in os.environ else getattr(config, "SMTP_USER", "")).strip()
    raw_password = os.environ["SMTP_PASSWORD"] if "SMTP_PASSWORD" in os.environ else getattr(config, "SMTP_PASSWORD", "")
    # Gmail App Password thường có khoảng trắng nhóm 4 ký tự ("xxxx xxxx xxxx xxxx")
    smtp_password = "".join(raw_password.split())
    smtp_from = (os.environ.get("SMTP_FROM") or getattr(config, "SMTP_FROM", "") or smtp_user).strip()
    return {
        "host": smtp_host,
        "port": smtp_port,
        "user": smtp_user,
        "password": smtp_password,
        "from_addr": smtp_from,
    }


def _dispatch_smtp_email(
    to_addr: str,
    subject: str,
    text_body: str,
    html_body: str = "",
    reply_to: str = "",
) -> Dict[str, Any]:
    """Hàm dùng chung gửi MIME Email qua SMTP (TLS 587 hoặc SSL 465)."""
    clean_to = _clean_header_value(to_addr)
    clean_subject = _clean_header_value(subject)
    cfg = _get_smtp_settings()

    if not cfg["user"] or not cfg["password"]:
        return {
            "email_sent": False,
            "mode": "smtp_unconfigured",
            "recipient": clean_to,
            "subject": clean_subject,
        }

    msg = EmailMessage()
    msg["Subject"] = clean_subject
    msg["From"] = _clean_header_value(cfg["from_addr"])
    msg["To"] = clean_to
    clean_reply = _clean_header_value(reply_to)
    if clean_reply and "@" in clean_reply and " " not in clean_reply:
        msg["Reply-To"] = clean_reply
    msg.set_content(text_body, subtype="plain", charset="utf-8")
    if html_body:
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        return {
            "email_sent": True,
            "mode": "smtp",
            "recipient": clean_to,
            "subject": clean_subject,
        }
    except Exception as exc:
        return {
            "email_sent": False,
            "mode": "smtp_error",
            "error": str(exc),
            "recipient": clean_to,
            "subject": clean_subject,
        }


def _wrap_eco_html(title: str, intro: str, code_label: str, code_value: str, footer_note: str) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:16px;border:1px solid #e2e8f0;color:#0f172a;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
        <span style="font-size:20px;font-weight:800;color:#0f172a;">EcoLogix <span style="color:#059669;">AI</span></span>
      </div>
      <h2 style="margin:0 0 10px 0;font-size:18px;color:#065f46;">{escape(title)}</h2>
      <p style="font-size:14px;line-height:1.6;color:#334155;margin:0 0 18px 0;">{escape(intro)}</p>
      <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:16px;text-align:center;margin-bottom:18px;">
        <div style="font-size:12px;font-weight:700;color:#047857;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">{escape(code_label)}</div>
        <div style="font-family:Consolas,monospace;font-size:26px;font-weight:800;letter-spacing:4px;color:#064e3b;">{escape(code_value)}</div>
      </div>
      <p style="font-size:12px;line-height:1.5;color:#64748b;margin:0;">{escape(footer_note)}</p>
    </div>
    """.strip()


def send_verification_otp_email(to_email: str, name: str, otp_code: str, is_resend: bool = False) -> Dict[str, Any]:
    """Gửi email mã OTP kích hoạt tài khoản tới người dùng."""
    clean_name = _clean_header_value(name) or "Quý khách"
    action_txt = "gửi lại" if is_resend else "đăng ký"
    subject = f"[EcoLogix AI] Mã OTP kích hoạt tài khoản: {otp_code}"
    text_body = (
        f"Xin chào {clean_name},\n\n"
        f"Bạn vừa yêu cầu {action_txt} tài khoản trên nền tảng EcoLogix AI.\n"
        f"Mã xác thực OTP của bạn là: {otp_code}\n\n"
        "Vui lòng nhập mã OTP gồm 6 chữ số này tại màn hình Xác thực tài khoản để hoàn tất kích hoạt.\n"
        "Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.\n\n"
        "Trân trọng,\nĐội ngũ EcoLogix AI"
    )
    html_body = _wrap_eco_html(
        title="Xác thực tài khoản EcoLogix AI",
        intro=f"Xin chào {clean_name}, mã xác thực OTP 6 chữ số cho yêu cầu {action_txt} tài khoản của bạn là:",
        code_label="Mã OTP kích hoạt",
        code_value=otp_code,
        footer_note="Nhập mã này tại trang Xác thực tài khoản để kích hoạt và đăng nhập vào hệ thống.",
    )
    return _dispatch_smtp_email(to_email, subject, text_body, html_body=html_body)


def send_password_reset_email(to_email: str, name: str, reset_token: str) -> Dict[str, Any]:
    """Gửi email mã khôi phục mật khẩu tới người dùng."""
    clean_name = _clean_header_value(name) or "Quý khách"
    subject = f"[EcoLogix AI] Mã khôi phục mật khẩu: {reset_token}"
    text_body = (
        f"Xin chào {clean_name},\n\n"
        "Hệ thống EcoLogix AI đã nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.\n"
        f"Mã khôi phục của bạn là: {reset_token}\n\n"
        "Vui lòng nhập mã này cùng mật khẩu mới tại tab Quên MK để cập nhật quyền truy cập.\n"
        "Nếu không phải bạn yêu cầu, hãy bỏ qua email này.\n\n"
        "Trân trọng,\nĐội ngũ EcoLogix AI"
    )
    html_body = _wrap_eco_html(
        title="Khôi phục mật khẩu EcoLogix AI",
        intro=f"Xin chào {clean_name}, sử dụng mã xác nhận bên dưới tại mục Quên MK để đặt lại mật khẩu mới:",
        code_label="Mã khôi phục mật khẩu",
        code_value=reset_token,
        footer_note="Vì lý do bảo mật, không chia sẻ mã khôi phục này cho người khác.",
    )
    return _dispatch_smtp_email(to_email, subject, text_body, html_body=html_body)


def send_contact_email(
    name: str,
    contact: str,
    need: str = "Dùng thử miễn phí 14 ngày",
    message: str = "",
    source: str = "Đặt lịch Tư vấn & Dùng thử 1-1 / FAQ",
    recipient: str = "",
) -> Dict[str, Any]:
    """Gửi yêu cầu tư vấn/FAQ tới email đích qua SMTP (nếu có) và trả về liên kết fallback."""
    to_addr = _clean_header_value(recipient or get_contact_recipient())
    clean_name = _clean_header_value(name)
    clean_contact = _clean_header_value(contact)
    clean_need = _clean_header_value(need or "Tư vấn EcoLogix AI")
    clean_source = _clean_header_value(source or "Landing Contact")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = _clean_header_value(f"[EcoLogix AI] {clean_need} - {clean_name}")
    body_text = (
        "YÊU CẦU TƯ VẤN / HỎI ĐÁP MỚI TỪ ECOLOGIX AI\n"
        "===========================================\n"
        f"- Nguồn gửi      : {clean_source}\n"
        f"- Thời gian      : {timestamp}\n"
        f"- Họ tên / DN    : {clean_name}\n"
        f"- Email / SĐT    : {clean_contact}\n"
        f"- Nhu cầu        : {clean_need}\n"
        f"- Nội dung       :\n{(message or '(Không có ghi chú thêm)').strip()}\n"
    )

    mailto_url = build_mailto_url(to_addr, subject, body_text)
    gmail_url = build_gmail_compose_url(to_addr, subject, body_text)

    res = _dispatch_smtp_email(to_addr, subject, body_text, reply_to=clean_contact)
    if not res["email_sent"]:
        res["mode"] = "mailto_fallback"
    res["mailto_url"] = mailto_url
    res["gmail_compose_url"] = gmail_url
    return res
