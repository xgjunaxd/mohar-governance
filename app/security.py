"""Security helpers for Mohar (no extra packages needed).

- SecurityHeadersMiddleware : adds browser security headers to every response
- RateLimitMiddleware       : per-IP limits + a global cap on AI (Gemini) calls
"""
import os
import re
import time
import threading
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not request.url.path.startswith(DOC_PATHS):
            # API only returns JSON, so nothing should ever load or run from it.
            h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
            h["Cache-Control"] = "no-store"
        return response


class _Window:
    """Sliding-window counter for one key."""
    __slots__ = ("hits",)

    def __init__(self):
        self.hits = deque()

    def allow(self, limit, period, now):
        while self.hits and now - self.hits[0] > period:
            self.hits.popleft()
        if len(self.hits) >= limit:
            return False, max(1, int(period - (now - self.hits[0])))
        self.hits.append(now)
        return True, 0


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


AI_PATH = re.compile(r"^/api/submissions(/[^/]+/resubmit)?$")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Protects the Gemini quota and the database from floods.

    Defaults (change with env vars on Render):
      RATE_LIMIT_AI_PER_MIN    = 10   AI reviews per IP per minute
      RATE_LIMIT_WRITE_PER_MIN = 30   other writes per IP per minute
      RATE_LIMIT_READ_PER_MIN  = 240  reads per IP per minute
      RATE_LIMIT_AI_GLOBAL_HR  = 300  AI reviews for ALL visitors per hour
    """

    def __init__(self, app):
        super().__init__(app)
        self.lock = threading.Lock()
        self.windows = {}
        self.ai_ip = _int_env("RATE_LIMIT_AI_PER_MIN", 10)
        self.write_ip = _int_env("RATE_LIMIT_WRITE_PER_MIN", 30)
        self.read_ip = _int_env("RATE_LIMIT_READ_PER_MIN", 240)
        self.ai_global = _int_env("RATE_LIMIT_AI_GLOBAL_HR", 300)

    @staticmethod
    def client_ip(request):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check(self, key, limit, period):
        now = time.monotonic()
        with self.lock:
            if len(self.windows) > 20000:  # keep memory bounded
                self.windows.clear()
            win = self.windows.setdefault(key, _Window())
            return win.allow(limit, period, now)

    async def dispatch(self, request, call_next):
        path, method = request.url.path, request.method
        if method == "OPTIONS" or path == "/health":
            return await call_next(request)

        ip = self.client_ip(request)
        checks = []
        if method == "POST" and AI_PATH.match(path):
            checks.append((f"ai:{ip}", self.ai_ip, 60))
            checks.append(("ai:global", self.ai_global, 3600))
        elif method in ("POST", "PUT", "DELETE", "PATCH"):
            checks.append((f"w:{ip}", self.write_ip, 60))
        else:
            checks.append((f"r:{ip}", self.read_ip, 60))

        for key, limit, period in checks:
            ok, retry = self._check(key, limit, period)
            if not ok:
                return JSONResponse(
                    {"detail": "Too many requests. Please wait a moment and try again."},
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                )
        return await call_next(request)
