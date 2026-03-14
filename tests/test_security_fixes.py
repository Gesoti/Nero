"""Tests for security audit remediation (H1, H2, M1-M4, L1, L2)."""
from __future__ import annotations

import httpx
import pytest

from app.blog import load_post, _SLUG_RE


# ── H1: Blog Markdown XSS prevention ──────────────────────────────────


def test_blog_slug_regex_rejects_path_traversal() -> None:
    """Slug regex must reject path traversal sequences."""
    assert _SLUG_RE.match("../etc/passwd") is None
    assert _SLUG_RE.match("../../secret") is None
    assert _SLUG_RE.match(".hidden") is None


def test_blog_slug_regex_accepts_valid_slugs() -> None:
    """Slug regex must accept normal blog slugs."""
    assert _SLUG_RE.match("valid-slug") is not None
    assert _SLUG_RE.match("post-2026-03") is not None
    assert _SLUG_RE.match("a") is not None


def test_load_post_rejects_traversal() -> None:
    """load_post must return None for path traversal slugs."""
    assert load_post("../../../etc/passwd") is None
    assert load_post("..") is None
    assert load_post(".hidden-file") is None


def test_load_post_rejects_slash_in_slug() -> None:
    """load_post must return None for slugs containing slashes."""
    assert load_post("foo/bar") is None
    assert load_post("/etc/passwd") is None


# ── M3: Open redirect prevention ──────────────────────────────────────


async def test_set_lang_blocks_protocol_relative_redirect(
    async_client: httpx.AsyncClient,
) -> None:
    """//evil.com must be rejected as an open redirect."""
    resp = await async_client.get(
        "/set-lang?lang=en&next=//evil.com", follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


async def test_set_lang_blocks_backslash_redirect(
    async_client: httpx.AsyncClient,
) -> None:
    """/\\evil.com must be rejected."""
    resp = await async_client.get(
        "/set-lang?lang=en&next=/\\evil.com", follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


async def test_set_lang_allows_valid_path(
    async_client: httpx.AsyncClient,
) -> None:
    """Normal relative paths like /gr/map must still work."""
    resp = await async_client.get(
        "/set-lang?lang=en&next=/gr/map", follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/gr/map"


# ── M1+M2+I1: CSP, HSTS, upgrade-insecure-requests ──────────────────


async def test_csp_script_src_no_unsafe_inline_or_eval(
    async_client: httpx.AsyncClient,
) -> None:
    """CSP script-src must not contain unsafe-inline or unsafe-eval."""
    resp = await async_client.get("/health")
    csp = resp.headers.get("content-security-policy", "")
    # Extract only the script-src directive
    script_src = [d for d in csp.split(";") if "script-src" in d and "insecure" not in d]
    assert len(script_src) == 1
    assert "'unsafe-inline'" not in script_src[0]
    assert "'unsafe-eval'" not in script_src[0]


async def test_csp_has_strict_dynamic(
    async_client: httpx.AsyncClient,
) -> None:
    """CSP script-src must contain strict-dynamic."""
    resp = await async_client.get("/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "'strict-dynamic'" in csp


async def test_csp_has_nonce(
    async_client: httpx.AsyncClient,
) -> None:
    """CSP script-src must contain a nonce."""
    resp = await async_client.get("/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "'nonce-" in csp


async def test_hsts_header_present(
    async_client: httpx.AsyncClient,
) -> None:
    """HSTS header must be set on all responses."""
    resp = await async_client.get("/health")
    hsts = resp.headers.get("strict-transport-security", "")
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


async def test_csp_has_upgrade_insecure_requests(
    async_client: httpx.AsyncClient,
) -> None:
    """CSP must include upgrade-insecure-requests directive."""
    resp = await async_client.get("/health")
    csp = resp.headers.get("content-security-policy", "")
    assert "upgrade-insecure-requests" in csp


# ── L1: Secure cookie flag ───────────────────────────────────────────


async def test_set_lang_cookie_has_secure_flag(
    async_client: httpx.AsyncClient,
) -> None:
    """wl_lang cookie must have the Secure flag."""
    resp = await async_client.get("/set-lang?lang=en", follow_redirects=False)
    cookie_header = resp.headers.get("set-cookie", "")
    assert "Secure" in cookie_header
