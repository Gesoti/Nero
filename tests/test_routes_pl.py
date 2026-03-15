"""
Smoke tests for Polish (/pl/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Poland routes gracefully degrade
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
async def pl_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,pl so the /pl/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,pl"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "pl"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def pl_seeded_client(in_memory_db):
    """pl_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,pl"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "pl"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Polish route smoke tests (empty data) ────────────────────────────────────

async def test_pl_dashboard_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert resp.status_code == 200


async def test_pl_dashboard_uses_pl_lang(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert 'lang="pl"' in resp.text


async def test_pl_map_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/map")
    assert resp.status_code == 200


async def test_pl_blog_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/blog")
    assert resp.status_code == 200


async def test_pl_about_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/about")
    assert resp.status_code == 200


async def test_pl_privacy_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/privacy")
    assert resp.status_code == 200


async def test_pl_health_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/health")
    assert resp.status_code == 200


async def test_pl_robots_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_pl_ads_txt_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_pl_sitemap_returns_200(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────────

async def test_pl_dashboard_has_og_meta(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert "og:title" in resp.text


async def test_pl_dashboard_has_description_meta(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert 'name="description"' in resp.text


async def test_pl_dashboard_security_headers(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_pl_dam_detail_returns_200(pl_seeded_client: httpx.AsyncClient) -> None:
    resp = await pl_seeded_client.get("/pl/dam/Kouris")
    assert resp.status_code == 200


async def test_pl_dam_detail_nonexistent_returns_404(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap inclusion ─────────────────────────────────────────────────────────

async def test_pl_sitemap_includes_pl_routes(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/sitemap.xml")
    assert "/pl/" in resp.text


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_pl_footer_has_imgw_attribution(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert "IMGW" in resp.text


# ── Country nav includes Poland ──────────────────────────────────────────────

async def test_pl_nav_includes_poland(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/pl/")
    assert "Poland" in resp.text or "PL" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_pl_enabled(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works_with_pl_enabled(pl_client: httpx.AsyncClient) -> None:
    resp = await pl_client.get("/health")
    assert resp.status_code == 200
