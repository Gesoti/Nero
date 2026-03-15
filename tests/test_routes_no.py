"""
Smoke tests for Norwegian (/no/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Norway routes gracefully degrade
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
async def no_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,fi,no so the /no/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi,no"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi", "no"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def no_seeded_client(in_memory_db):
    """no_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi,no"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi", "no"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Norwegian route smoke tests (empty data) ────────────────────────────────

async def test_no_dashboard_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert resp.status_code == 200


async def test_no_dashboard_uses_nb_lang(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert 'lang="nb"' in resp.text


async def test_no_map_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/map")
    assert resp.status_code == 200


async def test_no_blog_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/blog")
    assert resp.status_code == 200


async def test_no_about_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/about")
    assert resp.status_code == 200


async def test_no_privacy_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/privacy")
    assert resp.status_code == 200


async def test_no_health_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/health")
    assert resp.status_code == 200


async def test_no_robots_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_no_ads_txt_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_no_sitemap_returns_200(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────────

async def test_no_dashboard_has_og_meta(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert "og:title" in resp.text


async def test_no_dashboard_has_description_meta(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert 'name="description"' in resp.text


async def test_no_dashboard_security_headers(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_no_dam_detail_returns_200(no_seeded_client: httpx.AsyncClient) -> None:
    resp = await no_seeded_client.get("/no/dam/Kouris")
    assert resp.status_code == 200


async def test_no_dam_detail_nonexistent_returns_404(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap inclusion ─────────────────────────────────────────────────────────

async def test_no_sitemap_includes_no_routes(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/sitemap.xml")
    assert "/no/" in resp.text


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_no_footer_has_nve_attribution(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert "NVE" in resp.text


# ── Country nav includes Norway ───────────────────────────────────────────────

async def test_no_nav_includes_norway(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/no/")
    assert "Norway" in resp.text or "NO" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_no_enabled(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works_with_no_enabled(no_client: httpx.AsyncClient) -> None:
    resp = await no_client.get("/health")
    assert resp.status_code == 200
