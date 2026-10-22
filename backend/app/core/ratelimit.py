"""
LAYER 4 — internal protection.
- Per-IP rate limiting (fixed window) to blunt abuse / brute-force.
- Baseline security response headers.

Note: the limiter is in-process. For multi-worker deployments behind the proxy,
back it with Redis (a drop-in using settings.REDIS_URL) — the interface stays the
same. Container isolation (DB/Redis not exposed) and the audit log cover the rest
of this layer at the infrastructure level.
"""
import time
import ipaddress
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

_WINDOW = 60  # seconds
_hits: dict[str, list[float]] = defaultdict(list)
_auth_hits: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    trusted = {item.strip() for item in settings.TRUSTED_PROXY_IPS.split(",") if item.strip()}
    if peer in trusted:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit = settings.RATE_LIMIT_PER_MINUTE
        if limit > 0 and not request.url.path.startswith(("/health", "/docs", "/openapi")):
            ip = client_ip(request)
            now = time.time()
            auth_path = request.url.path in {
                "/auth/login", "/auth/register", "/auth/forgot-password",
                "/auth/reset-password", "/auth/refresh", "/auth/oauth/exchange",
            }
            effective_limit = settings.AUTH_RATE_LIMIT_PER_MINUTE if auth_path else limit
            buckets = _auth_hits if auth_path else _hits
            bucket = buckets[f"{ip}:{request.url.path}" if auth_path else ip]
            # drop timestamps older than the window
            cutoff = now - _WINDOW
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= effective_limit:
                return JSONResponse({"detail": "Too many requests"}, status_code=429)
            bucket.append(now)
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        r = await call_next(request)
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        r.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if settings.ENV == "production":
            r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return r
