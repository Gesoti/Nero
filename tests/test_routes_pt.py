"""
Smoke tests for Portuguese (/pt/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Portugal routes gracefully degrade
with empty data — no seeding required.
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
async def pt_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt so the /pt/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def pt_seeded_client(in_memory_db):
    """pt_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Portuguese route smoke tests (empty data) ────────────────────────────

async def test_pt_dashboard_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert resp.status_code == 200


async def test_pt_dashboard_uses_en_lang(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert 'lang="en"' in resp.text


async def test_pt_map_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/map")
    assert resp.status_code == 200


async def test_pt_blog_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/blog")
    assert resp.status_code == 200


async def test_pt_about_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/about")
    assert resp.status_code == 200


async def test_pt_privacy_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/privacy")
    assert resp.status_code == 200


async def test_pt_health_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/health")
    assert resp.status_code == 200


async def test_pt_robots_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_pt_ads_txt_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_pt_sitemap_returns_200(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────

async def test_pt_dashboard_has_og_meta(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert 'og:title' in resp.text


async def test_pt_dashboard_has_description_meta(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert 'name="description"' in resp.text


async def test_pt_dashboard_security_headers(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ─────────────────────────────────────────────────────

async def test_pt_dam_detail_returns_200(pt_seeded_client: httpx.AsyncClient) -> None:
    resp = await pt_seeded_client.get("/pt/dam/Kouris")
    assert resp.status_code == 200


async def test_pt_dam_detail_nonexistent_returns_404(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap dam inclusion ────────────────────────────────────────────────

async def test_pt_sitemap_includes_pt_routes(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/sitemap.xml")
    assert "/pt/" in resp.text


async def test_pt_sitemap_includes_alqueva(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/sitemap.xml")
    assert "/pt/dam/Alqueva" in resp.text


# ── Footer attribution ──────────────────────────────────────────────────

async def test_pt_footer_has_snirh_attribution(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert "SNIRH" in resp.text or "APA" in resp.text or "InfoAgua" in resp.text


# ── Country nav includes Portugal ────────────────────────────────────────

async def test_pt_nav_includes_portugal(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/pt/")
    assert "Portugal" in resp.text


# ── Cyprus routes still work ────────────────────────────────────────────

async def test_cy_routes_still_work(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works(pt_client: httpx.AsyncClient) -> None:
    resp = await pt_client.get("/health")
    assert resp.status_code == 200
