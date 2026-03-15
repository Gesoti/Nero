"""
Smoke tests for Czech (/cz/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Czech routes gracefully degrade
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
async def cz_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr,es,pt,cz so the /cz/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,cz"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "cz"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def cz_seeded_client(in_memory_db):
    """cz_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,cz"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "cz"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Czech route smoke tests (empty data) ────────────────────────────────────

async def test_cz_dashboard_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/")
    assert resp.status_code == 200


async def test_cz_dashboard_uses_en_lang(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/")
    assert 'lang="en"' in resp.text


async def test_cz_map_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/map")
    assert resp.status_code == 200


async def test_cz_blog_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/blog")
    assert resp.status_code == 200


async def test_cz_about_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/about")
    assert resp.status_code == 200


async def test_cz_privacy_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/privacy")
    assert resp.status_code == 200


async def test_cz_health_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/health")
    assert resp.status_code == 200


async def test_cz_robots_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/robots.txt")
    assert resp.status_code == 200


async def test_cz_ads_txt_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/ads.txt")
    assert resp.status_code == 200


async def test_cz_sitemap_returns_200(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── Security headers ─────────────────────────────────────────────────────────

async def test_cz_dashboard_security_headers(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/cz/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Cyprus routes still work ─────────────────────────────────────────────────

async def test_cy_routes_still_work(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_still_works(cz_client: httpx.AsyncClient) -> None:
    resp = await cz_client.get("/health")
    assert resp.status_code == 200
