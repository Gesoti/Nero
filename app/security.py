"""
HTTP security headers middleware.

CSP strategy:
  Approach A (current) — strict allowlist for our CDNs, no AdSense.
  Approach B (Phase 6) — nonce-based with unsafe-eval for Google AdSense.
  Switching to B requires: generating a per-request nonce, injecting it into
  every <script nonce="..."> and <style nonce="..."> tag in the templates,
  and passing it via request.state.csp_nonce to the Jinja2 context.
"""
from __future__ import annotations

from fastapi import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# CDN allowlist (Approach A — without AdSense)
_CDN_JSDELIVR     = "https://cdn.jsdelivr.net"
_GOOGLE_FONTS_CSS = "https://fonts.googleapis.com"
_GOOGLE_FONTS_TTF = "https://fonts.gstatic.com"

_CSP = (
    "default-src 'self'; "
    f"script-src 'self' {_CDN_JSDELIVR}; "
    f"style-src 'self' 'unsafe-inline' {_GOOGLE_FONTS_CSS} {_CDN_JSDELIVR}; "
    f"font-src {_GOOGLE_FONTS_TTF}; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)

# ── Approach B — with Google AdSense (activate in Phase 6) ───────────────────
# Uncomment and replace _CSP with _CSP_WITH_ADS once AdSense is approved.
# Also: generate a per-request nonce, store in request.state.csp_nonce,
# and apply nonce="{{ request.state.csp_nonce }}" to every <script> and
# <style nonce> tag in base.html.
#
# _CDN_ADSENSE_FRAME = (
#     "https://googleads.g.doubleclick.net "
#     "https://tpc.googlesyndication.com"
# )
# _CSP_WITH_ADS = (
#     "default-src 'self'; "
#     "script-src 'nonce-{nonce}' 'unsafe-inline' 'unsafe-eval' 'strict-dynamic' https:; "
#     "style-src 'nonce-{nonce}' 'unsafe-inline' {_GOOGLE_FONTS_CSS}; "
#     f"font-src {_GOOGLE_FONTS_TTF}; "
#     "img-src 'self' data: https:; "
#     "connect-src 'self' https:; "
#     f"frame-src {_CDN_ADSENSE_FRAME}; "
#     "frame-ancestors 'none'; "
#     "base-uri 'self'; "
#     "object-src 'none'"
# )
# ─────────────────────────────────────────────────────────────────────────────

_PERMISSIONS = (
    "accelerometer=(), camera=(), display-capture=(), "
    "geolocation=(), gyroscope=(), magnetometer=(), "
    "microphone=(), payment=(), usb=()"
)


async def security_headers_middleware(request: Request, call_next) -> Response:
    """Inject security headers into every response."""
    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"]        = "DENY"
    h["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    h["Permissions-Policy"]     = _PERMISSIONS
    h["Content-Security-Policy"] = _CSP
    return response
