"""
Smoke tests for Bulgarian (/bg/) routes.
Uses httpx.AsyncClient with in-memory SQLite. Bulgaria routes gracefully
degrade with empty data — no seeding required for basic smoke tests.
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
async def bg_client(in_memory_db):
    """
    Client with enabled_countries including 'bg' so the /bg/ prefix is active.
    """
    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi,no,bg"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi", "no", "bg"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def bg_seeded_client(in_memory_db):
    """bg_client with one dam + percentage pre-seeded for dam-related assertions."""
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt,fi,no,bg"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt", "fi", "no", "bg"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Bulgarian route smoke tests ──────────────────────────────────────────────

async def test_bg_dashboard_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert resp.status_code == 200


async def test_bg_dashboard_uses_bg_lang(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert 'lang="bg"' in resp.text


async def test_bg_map_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/map")
    assert resp.status_code == 200


async def test_bg_blog_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/blog")
    assert resp.status_code == 200


async def test_bg_about_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/about")
    assert resp.status_code == 200


async def test_bg_privacy_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/privacy")
    assert resp.status_code == 200


async def test_bg_health_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/health")
    assert resp.status_code == 200


async def test_bg_sitemap_returns_200(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/sitemap.xml")
    assert resp.status_code == 200


# ── SEO & meta tag tests ──────────────────────────────────────────────────────

async def test_bg_dashboard_has_og_meta(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "og:title" in resp.text


async def test_bg_dashboard_has_description_meta(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert 'name="description"' in resp.text


async def test_bg_dashboard_security_headers(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


# ── Dam detail tests ──────────────────────────────────────────────────────────

async def test_bg_dam_detail_returns_200(bg_seeded_client: httpx.AsyncClient) -> None:
    resp = await bg_seeded_client.get("/bg/dam/Kouris")
    assert resp.status_code == 200


async def test_bg_dam_detail_nonexistent_returns_404(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/dam/NonexistentDam")
    assert resp.status_code == 404


# ── Footer attribution ────────────────────────────────────────────────────────

async def test_bg_footer_has_moew_attribution(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "MOEW" in resp.text


# ── Sitemap inclusion ─────────────────────────────────────────────────────────

async def test_bg_sitemap_includes_bg_routes(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/sitemap.xml")
    assert "/bg/" in resp.text


# ── Country nav includes Bulgaria ─────────────────────────────────────────────

async def test_bg_nav_includes_bulgaria(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "Bulgaria" in resp.text or "BG" in resp.text


# ── og:locale is bg_BG ───────────────────────────────────────────────────────

async def test_bg_dashboard_has_bg_locale(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "bg_BG" in resp.text


# ── Cyprus routes still work ──────────────────────────────────────────────────

async def test_cy_routes_still_work_with_bg_enabled(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/")
    assert resp.status_code == 200
