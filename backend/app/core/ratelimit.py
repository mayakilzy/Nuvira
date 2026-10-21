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
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

_WINDOW = 60  # seconds
_hits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit = settings.RATE_LIMIT_PER_MINUTE
        if limit > 0 and not request.url.path.startswith(("/health", "/docs", "/openapi")):
            ip = (request.client.host if request.client else "unknown")
            now = time.time()
            bucket = _hits[ip]
            # drop timestamps older than the window
            cutoff = now - _WINDOW
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= limit:
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
        return r
