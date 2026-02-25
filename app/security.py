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

_GOOGLE_FONTS_CSS = "https://fonts.googleapis.com"
_GOOGLE_FONTS_TTF = "https://fonts.gstatic.com"

_CDN_ADSENSE_FRAME = (
    "https://googleads.g.doubleclick.net "
    "https://tpc.googlesyndication.com"
)

_CSP_TEMPLATE = (
    "default-src 'self'; "
    "script-src 'nonce-{nonce}' 'unsafe-inline' 'unsafe-eval' 'strict-dynamic' https:; "
    "style-src 'nonce-{nonce}' 'unsafe-inline' {fonts_css}; "
    "font-src {fonts_ttf}; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https:; "
    "frame-src {adsense_frame}; "
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


def _generate_nonce() -> str:
    """Generate a cryptographically random base64 nonce (24 bytes → 32 chars)."""
    return secrets.token_urlsafe(24)


async def security_headers_middleware(request: Request, call_next) -> Response:
    """Inject security headers into every response with a per-request CSP nonce."""
    nonce = _generate_nonce()
    request.state.csp_nonce = nonce

    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"]        = "DENY"
    h["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    h["Permissions-Policy"]     = _PERMISSIONS
    h["Content-Security-Policy"] = _CSP_TEMPLATE.format(
        nonce=nonce,
        fonts_css=_GOOGLE_FONTS_CSS,
        fonts_ttf=_GOOGLE_FONTS_TTF,
        adsense_frame=_CDN_ADSENSE_FRAME,
    )
    return response
