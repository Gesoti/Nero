"""
Smoke tests for Spanish (/es/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Spain routes gracefully degrade
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
async def es_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es so the /es/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def es_seeded_client(in_memory_db):
    """es_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Spanish route smoke tests (empty data) ────────────────────────────────

async def test_es_dashboard_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/")
    assert resp.status_code == 200


async def test_es_dashboard_uses_en_lang(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert 'lang="en"' in resp.text


async def test_es_health_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/health")
    assert resp.status_code == 200


async def test_es_map_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/map")
    assert resp.status_code == 200


async def test_es_about_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/about")
    assert resp.status_code == 200


async def test_es_privacy_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/privacy")
    assert resp.status_code == 200


async def test_es_blog_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/blog")
    assert resp.status_code == 200


async def test_es_robots_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/robots.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


async def test_es_ads_txt_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/ads.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


async def test_es_sitemap_returns_200(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]


# ── Spanish SEO and content tests ─────────────────────────────────────────

async def test_es_dashboard_has_meta_description(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert '<meta name="description"' in resp.text


async def test_es_dashboard_has_og_tags(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert '<meta property="og:title"' in resp.text
    assert '<meta property="og:description"' in resp.text
    assert '<meta property="og:type"' in resp.text


async def test_es_dashboard_security_headers(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert "content-security-policy" in resp.headers
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


# ── Spain layout / footer attribution ────────────────────────────────────

async def test_es_footer_has_embalses_attribution(es_client: httpx.AsyncClient) -> None:
    """Spanish pages should credit embalses.net as data source."""
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert "embalses.net" in resp.text


async def test_es_footer_has_miteco_attribution(es_client: httpx.AsyncClient) -> None:
    """Spanish pages should credit MITECO as data source."""
    resp = await es_client.get("/es/")
    assert resp.status_code == 200
    assert "MITECO" in resp.text


# ── Dam detail routes with seeded data ────────────────────────────────────

async def test_es_dam_detail_returns_200(es_seeded_client: httpx.AsyncClient) -> None:
    resp = await es_seeded_client.get("/es/dam/Kouris")
    assert resp.status_code == 200


async def test_es_dam_detail_contains_dam_name(es_seeded_client: httpx.AsyncClient) -> None:
    resp = await es_seeded_client.get("/es/dam/Kouris")
    assert resp.status_code == 200
    assert "Kouris" in resp.text


async def test_es_dam_detail_nonexistent_returns_404(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/es/dam/nonexistent-dam-xyz")
    assert resp.status_code == 404


# ── Sitemap includes Spain dams ───────────────────────────────────────────

async def test_sitemap_includes_spain_dams(es_client: httpx.AsyncClient) -> None:
    """Sitemap should include /es/dam/ URLs for Spain's static dam list."""
    resp = await es_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/es/dam/La%20Serena" in resp.text
    assert "/es/dam/Alcantara" in resp.text


async def test_sitemap_includes_spain_main_pages(es_client: httpx.AsyncClient) -> None:
    """Sitemap should include /es/ main pages."""
    resp = await es_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/es/" in resp.text
    assert "/es/map" in resp.text


# ── Cyprus routes unaffected by Spain enable ──────────────────────────────

async def test_cy_routes_still_work_with_spain(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works_with_spain(es_client: httpx.AsyncClient) -> None:
    resp = await es_client.get("/health")
    assert resp.status_code == 200


# ── Country navigation includes Spain ─────────────────────────────────────

async def test_country_nav_includes_spain(es_client: httpx.AsyncClient) -> None:
    """When Spain is enabled, the country nav should show Spain."""
    resp = await es_client.get("/")
    assert resp.status_code == 200
    assert "Spain" in resp.text
