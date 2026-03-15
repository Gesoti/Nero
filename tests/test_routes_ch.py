"""
Smoke tests for Swiss (/ch/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Swiss routes gracefully degrade
with empty data — no seeding required for basic 200-status checks.
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
async def ch_client(in_memory_db):
    """
    Client with enabled_countries including 'ch' so the /ch/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,ch"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "ch"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def ch_seeded_client(in_memory_db):
    """ch_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,ch"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "ch"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Swiss route smoke tests ──────────────────────────────────────────────────

async def test_ch_dashboard_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert resp.status_code == 200


async def test_ch_dashboard_uses_de_lang(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert 'lang="de"' in resp.text


async def test_ch_map_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/map")
    assert resp.status_code == 200


async def test_ch_blog_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/blog")
    assert resp.status_code == 200


async def test_ch_about_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/about")
    assert resp.status_code == 200


async def test_ch_privacy_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/privacy")
    assert resp.status_code == 200


async def test_ch_health_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/health")
    assert resp.status_code == 200


async def test_ch_sitemap_returns_200(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ─────────────────────────────────────────────────────

async def test_ch_dashboard_has_og_meta(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert "og:title" in resp.text


async def test_ch_dashboard_has_description_meta(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert 'name="description"' in resp.text


async def test_ch_dashboard_security_headers(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_ch_dam_detail_returns_200(ch_seeded_client: httpx.AsyncClient) -> None:
    resp = await ch_seeded_client.get("/ch/dam/Kouris")
    assert resp.status_code == 200


async def test_ch_dam_detail_nonexistent_returns_404(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_ch_footer_has_bfe_attribution(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert "BFE" in resp.text or "SFOE" in resp.text


# ── Country nav includes Switzerland ─────────────────────────────────────────

async def test_ch_nav_includes_switzerland(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/ch/")
    assert "Switzerland" in resp.text or "CH" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_ch_enabled(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/")
    assert resp.status_code == 200


# ── Sitemap includes Switzerland routes ───────────────────────────────────────

async def test_ch_sitemap_includes_ch_routes(ch_client: httpx.AsyncClient) -> None:
    resp = await ch_client.get("/sitemap.xml")
    assert "/ch/" in resp.text
