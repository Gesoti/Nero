"""
Smoke tests for Greek (/gr/) routes (G11).
Uses httpx.AsyncClient with in-memory SQLite. Greece routes gracefully degrade
with empty data — no seeding required.

These tests import the gr_client fixture from test_multi_country_routes.py which
properly patches the CountryPrefixMiddleware to recognize /gr/ prefix routes.
"""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.config import settings
from app.db import upsert_dams, upsert_percentage_snapshot
from app.main import app
from app.middleware.country import CountryPrefixMiddleware
from tests.conftest import _DamStub, _SnapshotStub
from unittest.mock import patch


@pytest_asyncio.fixture
async def gr_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr so the /gr/ prefix is active.

    Patches settings.enabled_countries and wraps the app with CountryPrefixMiddleware
    to ensure the test client recognizes /gr/ as a valid country prefix.
    """
    with patch.object(settings, "enabled_countries", "cy,gr"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def gr_seeded_client(in_memory_db):
    """gr_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Greek route smoke tests (empty data) ──────────────────────────────────

async def test_gr_dashboard_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ must return 200 with empty data (graceful degradation)."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200


async def test_gr_dashboard_uses_el_lang(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ must render with lang="el" from gr/layout.html."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert 'lang="el"' in resp.text


async def test_gr_health_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/health must return 200."""
    resp = await gr_client.get("/gr/health")
    assert resp.status_code == 200


async def test_gr_map_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/map must return 200."""
    resp = await gr_client.get("/gr/map")
    assert resp.status_code == 200


async def test_gr_about_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/about must return 200."""
    resp = await gr_client.get("/gr/about")
    assert resp.status_code == 200


async def test_gr_privacy_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/privacy must return 200."""
    resp = await gr_client.get("/gr/privacy")
    assert resp.status_code == 200


async def test_gr_blog_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/blog must return 200."""
    resp = await gr_client.get("/gr/blog")
    assert resp.status_code == 200


async def test_gr_robots_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/robots.txt must return 200 and be text/plain."""
    resp = await gr_client.get("/gr/robots.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


async def test_gr_ads_txt_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ads.txt must return 200 and be text/plain."""
    resp = await gr_client.get("/gr/ads.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


async def test_gr_sitemap_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/sitemap.xml must return 200 and be XML."""
    resp = await gr_client.get("/gr/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]


# ── Greek SEO and content tests ───────────────────────────────────────────

async def test_gr_dashboard_has_meta_description(gr_client: httpx.AsyncClient) -> None:
    """Greek dashboard must have meta description for SEO."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert '<meta name="description"' in resp.text


async def test_gr_dashboard_has_og_tags(gr_client: httpx.AsyncClient) -> None:
    """Greek dashboard must have Open Graph tags."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert '<meta property="og:title"' in resp.text
    assert '<meta property="og:description"' in resp.text
    assert '<meta property="og:type"' in resp.text


async def test_gr_dashboard_has_el_gr_locale(gr_client: httpx.AsyncClient) -> None:
    """Greek dashboard must have el_GR locale in og:locale."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert "el_GR" in resp.text


async def test_gr_dashboard_security_headers(gr_client: httpx.AsyncClient) -> None:
    """Greek dashboard must have CSP and other security headers."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert "content-security-policy" in resp.headers
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


# ── Dam detail routes with seeded data ────────────────────────────────────

async def test_gr_dam_detail_returns_200(gr_seeded_client: httpx.AsyncClient) -> None:
    """GET /gr/dam/Kouris must return 200 with seeded data."""
    resp = await gr_seeded_client.get("/gr/dam/Kouris")
    assert resp.status_code == 200


async def test_gr_dam_detail_contains_dam_name(gr_seeded_client: httpx.AsyncClient) -> None:
    """Greek dam detail page must contain the dam name."""
    resp = await gr_seeded_client.get("/gr/dam/Kouris")
    assert resp.status_code == 200
    assert "Kouris" in resp.text


async def test_gr_dam_detail_nonexistent_returns_404(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/dam/nonexistent-dam must return 404."""
    resp = await gr_client.get("/gr/dam/nonexistent-dam-xyz")
    assert resp.status_code == 404


# ── Cyprus routes unaffected by Greece enable ────────────────────────────

async def test_cy_routes_still_work(gr_client: httpx.AsyncClient) -> None:
    """Cyprus routes must continue to work when Greece is enabled."""
    resp = await gr_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works(gr_client: httpx.AsyncClient) -> None:
    """Cyprus health endpoint must continue to work."""
    resp = await gr_client.get("/health")
    assert resp.status_code == 200


async def test_cy_map_still_works(gr_client: httpx.AsyncClient) -> None:
    """Cyprus map must continue to work."""
    resp = await gr_client.get("/map")
    assert resp.status_code == 200
