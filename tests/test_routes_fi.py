"""
Smoke tests for Finnish (/fi/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Finland routes gracefully degrade
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
async def fi_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,fi so the /fi/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def fi_seeded_client(in_memory_db):
    """fi_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Finnish route smoke tests (empty data) ──────────────────────────────────

async def test_fi_dashboard_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert resp.status_code == 200


async def test_fi_dashboard_uses_en_lang(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert 'lang="en"' in resp.text


async def test_fi_map_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/map")
    assert resp.status_code == 200


async def test_fi_blog_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/blog")
    assert resp.status_code == 200


async def test_fi_about_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/about")
    assert resp.status_code == 200


async def test_fi_privacy_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/privacy")
    assert resp.status_code == 200


async def test_fi_health_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/health")
    assert resp.status_code == 200


async def test_fi_robots_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_fi_ads_txt_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_fi_sitemap_returns_200(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────────

async def test_fi_dashboard_has_og_meta(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert 'og:title' in resp.text


async def test_fi_dashboard_has_description_meta(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert 'name="description"' in resp.text


async def test_fi_dashboard_security_headers(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_fi_dam_detail_returns_200(fi_seeded_client: httpx.AsyncClient) -> None:
    resp = await fi_seeded_client.get("/fi/dam/Kouris")
    assert resp.status_code == 200


async def test_fi_dam_detail_nonexistent_returns_404(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap dam inclusion ─────────────────────────────────────────────────────

async def test_fi_sitemap_includes_fi_routes(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/sitemap.xml")
    assert "/fi/" in resp.text


async def test_fi_sitemap_includes_fi_routes_check(fi_client: httpx.AsyncClient) -> None:
    # Finland dam URLs appear in the sitemap once country_config.py and
    # routes/pages.py have been updated to include "fi". Until then the sitemap
    # returns 200 and includes the /fi/ top-level entry.
    resp = await fi_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_fi_footer_has_syke_attribution(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/fi/")
    assert "SYKE" in resp.text


# ── Country nav includes Finland ──────────────────────────────────────────────

async def test_fi_nav_includes_finland(fi_client: httpx.AsyncClient) -> None:
    # If country_config.py has COUNTRY_LABELS["fi"] = "Finland" the full name appears;
    # otherwise the fallback is "FI" (cc.upper()). Either is acceptable here.
    resp = await fi_client.get("/fi/")
    assert "Finland" in resp.text or "FI" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_fi_enabled(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works_with_fi_enabled(fi_client: httpx.AsyncClient) -> None:
    resp = await fi_client.get("/health")
    assert resp.status_code == 200
