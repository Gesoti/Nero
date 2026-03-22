"""
HTTP security headers middleware.

CSP strategy: nonce-based with AdSense support.
A unique nonce is generated per request and stored in request.state.csp_nonce
for use in templates (e.g. <script nonce="{{ request.state.csp_nonce }}">).
"""
from __future__ import annotations

import secrets

from fastapi import Request
from starlette.responses import Response

_CSP_TEMPLATE = (
    "upgrade-insecure-requests; "
    "default-src 'self'; "
    "script-src 'nonce-{nonce}' 'strict-dynamic'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https:; "
    "frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)

_PERMISSIONS = (
    "accelerometer=(), camera=(), display-capture=(), "
    "geolocation=(), gyroscope=(), magnetometer=(), "
    "microphone=(), payment=(), usb=()"
)


async def security_headers_middleware(request: Request, call_next) -> Response:
    """Inject security headers into every response with a per-request CSP nonce."""
    nonce = secrets.token_urlsafe(24)
    request.state.csp_nonce = nonce

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = _PERMISSIONS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = _CSP_TEMPLATE.format(nonce=nonce)
    return response
