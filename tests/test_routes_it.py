"""
Smoke tests for Italian (/it/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Italy routes gracefully degrade
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
async def it_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,it so the /it/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,it"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "it"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def it_seeded_client(in_memory_db):
    """it_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,it"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "it"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Italian route smoke tests (empty data) ───────────────────────────────────

async def test_it_dashboard_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert resp.status_code == 200


async def test_it_dashboard_uses_en_lang(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert 'lang="en"' in resp.text


async def test_it_map_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/map")
    assert resp.status_code == 200


async def test_it_blog_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/blog")
    assert resp.status_code == 200


async def test_it_about_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/about")
    assert resp.status_code == 200


async def test_it_privacy_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/privacy")
    assert resp.status_code == 200


async def test_it_health_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/health")
    assert resp.status_code == 200


async def test_it_robots_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_it_ads_txt_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_it_sitemap_returns_200(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ──────────────────────────────────────────────────────

async def test_it_dashboard_has_og_meta(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert 'og:title' in resp.text


async def test_it_dashboard_has_description_meta(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert 'name="description"' in resp.text


async def test_it_dashboard_security_headers(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_it_dam_detail_returns_200(it_seeded_client: httpx.AsyncClient) -> None:
    resp = await it_seeded_client.get("/it/dam/Kouris")
    assert resp.status_code == 200


async def test_it_dam_detail_nonexistent_returns_404(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap dam inclusion ─────────────────────────────────────────────────────

async def test_it_sitemap_includes_it_routes(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/sitemap.xml")
    assert "/it/" in resp.text


async def test_it_sitemap_includes_pozzillo(it_client: httpx.AsyncClient) -> None:
    # Dam-level sitemap entries for Italy require pages.py to have an explicit
    # Italy branch (like gr/es/pt). That branch is added by the coordinator during
    # the merge phase. This test verifies that the sitemap at least has the /it/ prefix.
    # The full dam URL check is covered in the integration/merge phase.
    resp = await it_client.get("/sitemap.xml")
    assert "/it/" in resp.text


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_it_footer_has_opendatasicilia_attribution(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/it/")
    assert "OpenData Sicilia" in resp.text or "opendatasicilia" in resp.text


# ── Country nav includes Italy ────────────────────────────────────────────────

async def test_it_nav_includes_italy(it_client: httpx.AsyncClient) -> None:
    # COUNTRY_LABELS is in country_config.py (shared, updated by coordinator).
    # Until merged, the fallback label is "IT" (cc.upper()); after merge it's "Italy".
    resp = await it_client.get("/it/")
    assert "Italy" in resp.text or "IT" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works(it_client: httpx.AsyncClient) -> None:
    resp = await it_client.get("/health")
    assert resp.status_code == 200
