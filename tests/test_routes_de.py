"""
Smoke tests for German (/de/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Germany routes gracefully degrade
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
async def de_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,de so the /de/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,de"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "de"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def de_seeded_client(in_memory_db):
    """de_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,de"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "de"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── German route smoke tests (empty data) ────────────────────────────────────

async def test_de_dashboard_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert resp.status_code == 200


async def test_de_dashboard_uses_de_lang(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert 'lang="de"' in resp.text


async def test_de_map_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/map")
    assert resp.status_code == 200


async def test_de_blog_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/blog")
    assert resp.status_code == 200


async def test_de_about_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/about")
    assert resp.status_code == 200


async def test_de_privacy_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/privacy")
    assert resp.status_code == 200


async def test_de_health_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/health")
    assert resp.status_code == 200


async def test_de_robots_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_de_ads_txt_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_de_sitemap_returns_200(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────────

async def test_de_dashboard_has_og_meta(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert "og:title" in resp.text


async def test_de_dashboard_has_description_meta(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert 'name="description"' in resp.text


async def test_de_dashboard_security_headers(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_de_dam_detail_returns_200(de_seeded_client: httpx.AsyncClient) -> None:
    resp = await de_seeded_client.get("/de/dam/Kouris")
    assert resp.status_code == 200


async def test_de_dam_detail_nonexistent_returns_404(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Sitemap inclusion ─────────────────────────────────────────────────────────

async def test_de_sitemap_includes_de_routes(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/sitemap.xml")
    assert "/de/" in resp.text


async def test_de_sitemap_includes_bleiloch_dam(de_client: httpx.AsyncClient) -> None:
    """Sitemap must include /de/dam/Bleiloch from static provider metadata."""
    resp = await de_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/de/dam/Bleiloch" in resp.text


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_de_footer_has_ruhr_attribution(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    # Footer should attribute Talsperrenleitzentrale or LTV Sachsen
    assert "Talsperrenleitzentrale" in resp.text or "LTV" in resp.text


# ── Country nav includes Germany ──────────────────────────────────────────────

async def test_de_nav_includes_germany(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/de/")
    assert "Germany" in resp.text or "DE" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_de_enabled(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works_with_de_enabled(de_client: httpx.AsyncClient) -> None:
    resp = await de_client.get("/health")
    assert resp.status_code == 200
