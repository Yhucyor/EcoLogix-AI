"""
EcoLogix AI - Contact & Consultation Email Service
Hỗ trợ gửi email thực tế qua SMTP (nếu cấu hình SMTP_USER / SMTP_PASSWORD)
và luôn tạo kèm liên kết mailto: / Gmail Web compose chuẩn UTF-8 tới email tư vấn.
"""
from datetime import datetime
from email.message import EmailMessage
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

    smtp_host = (os.environ.get("SMTP_HOST") or getattr(config, "SMTP_HOST", "smtp.gmail.com")).strip()
    smtp_port = int(os.environ.get("SMTP_PORT") or getattr(config, "SMTP_PORT", 587))
    smtp_user = (os.environ.get("SMTP_USER") or getattr(config, "SMTP_USER", "")).strip()
    smtp_password = (os.environ.get("SMTP_PASSWORD") or getattr(config, "SMTP_PASSWORD", "")).strip()
    smtp_from = (os.environ.get("SMTP_FROM") or getattr(config, "SMTP_FROM", "") or smtp_user).strip()

    if not smtp_user or not smtp_password:
        return {
            "email_sent": False,
            "mode": "mailto_fallback",
            "recipient": to_addr,
            "subject": subject,
            "mailto_url": mailto_url,
            "gmail_compose_url": gmail_url,
        }

    email_msg = EmailMessage()
    email_msg["Subject"] = subject
    email_msg["From"] = smtp_from
    email_msg["To"] = to_addr
    if "@" in clean_contact and " " not in clean_contact:
        email_msg["Reply-To"] = clean_contact
    email_msg.set_content(body_text, subtype="plain", charset="utf-8")

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(email_msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.send_message(email_msg)

        return {
            "email_sent": True,
            "mode": "smtp",
            "recipient": to_addr,
            "subject": subject,
            "mailto_url": mailto_url,
            "gmail_compose_url": gmail_url,
        }
    except Exception as exc:
        return {
            "email_sent": False,
            "mode": "mailto_fallback",
            "error": str(exc),
            "recipient": to_addr,
            "subject": subject,
            "mailto_url": mailto_url,
            "gmail_compose_url": gmail_url,
        }

