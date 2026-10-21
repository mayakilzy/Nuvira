"""Transactional email via Resend. No SDK needed — simple HTTPS call."""
from __future__ import annotations

import httpx

from app.config import settings

RESEND_URL = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True on success; never raises into request flow."""
    if not settings.RESEND_API_KEY:
        # In dev without a key, log to stdout instead of failing.
        print(f"[email:dev] to={to} subject={subject}\n{html}")
        return True
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": settings.EMAIL_FROM, "to": [to], "subject": subject, "html": html},
            )
        return r.status_code < 300
    except Exception as e:
        print(f"[email:error] {e}")
        return False


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;padding:12px 24px;'
        f'background:#111;color:#fff;text-decoration:none;border-radius:8px">{label}</a>'
    )


async def send_verification_email(to: str, token: str) -> bool:
    url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"<h2>Confirm your email</h2><p>Welcome to {settings.APP_NAME}.</p><p>{_button(url, 'Verify email')}</p>"
    return await send_email(to, f"Verify your {settings.APP_NAME} email", html)


async def send_reset_email(to: str, token: str) -> bool:
    url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"<h2>Reset your password</h2><p>{_button(url, 'Reset password')}</p><p>If you didn't request this, ignore this email.</p>"
    return await send_email(to, f"Reset your {settings.APP_NAME} password", html)
