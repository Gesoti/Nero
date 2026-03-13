"""
Tests for G10: routes use request.state for per-country db_path, layout, and i18n.

These tests verify that:
- CY routes still work as before
- GR routes resolve correctly and render templates without errors
- The correct layout template is used per country
- country_prefix is passed in template context
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest_asyncio

from app.config import settings
from app.main import app
from app.middleware.country import CountryPrefixMiddleware


@pytest_asyncio.fixture
async def gr_client(in_memory_db):
    """
    Client with enabled_countries=cy,gr so the /gr/ prefix is active.

    We must patch settings.enabled_countries so that the CountryPrefixMiddleware
    that is already registered on the app (built from settings) also recognises
    "gr".  Without this patch, the inner middleware would overwrite country="cy"
    even after the outer test-wrapper sets country="gr".
    """
    from app.middleware.country import CountryPrefixMiddleware
    from app.config import settings as _settings

    with patch.object(_settings, "enabled_countries", "cy,gr"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest_asyncio.fixture
async def gr_seeded_client(in_memory_db):
    """gr_client with one dam + percentage pre-seeded."""
    from app.db import upsert_dams, upsert_percentage_snapshot
    from tests.conftest import _DamStub, _SnapshotStub
    from app.config import settings as _settings

    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(_settings, "enabled_countries", "cy,gr"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── CY routes still work ──────────────────────────────────────────────────────

async def test_cy_dashboard_returns_200(seeded_async_client: httpx.AsyncClient) -> None:
    resp = await seeded_async_client.get("/")
    assert resp.status_code == 200


async def test_cy_health_returns_200(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/health")
    assert resp.status_code == 200


async def test_cy_dashboard_uses_cy_layout(seeded_async_client: httpx.AsyncClient) -> None:
    """Cyprus dashboard must use cy/layout.html (lang=en, no el_GR)."""
    resp = await seeded_async_client.get("/")
    assert resp.status_code == 200
    # Default lang is "en" from cy/layout.html (which inherits base.html default)
    assert 'lang="el"' not in resp.text


# ── GR routes resolve correctly ───────────────────────────────────────────────

async def test_gr_health_returns_200(gr_client: httpx.AsyncClient) -> None:
    resp = await gr_client.get("/gr/health")
    assert resp.status_code == 200


async def test_gr_root_returns_200(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ must return 200 (may have empty data in tests — that's fine)."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200


async def test_gr_layout_renders_lang_el(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ must render with lang=el from gr/layout.html."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert 'lang="el"' in resp.text


async def test_gr_layout_renders_el_GR_locale(gr_client: httpx.AsyncClient) -> None:
    """GET /gr/ must render with og:locale=el_GR from gr/layout.html."""
    resp = await gr_client.get("/gr/")
    assert resp.status_code == 200
    assert "el_GR" in resp.text


async def test_gr_about_returns_200(gr_client: httpx.AsyncClient) -> None:
    resp = await gr_client.get("/gr/about")
    assert resp.status_code == 200


# ── layout_template is per-request, not global ───────────────────────────────

async def test_cy_and_gr_use_different_layouts(
    gr_seeded_client: httpx.AsyncClient,
) -> None:
    """Verify CY renders with en layout and GR with el layout in same test."""
    gr_resp = await gr_seeded_client.get("/gr/")
    cy_resp = await gr_seeded_client.get("/")
    assert gr_resp.status_code == 200
    assert cy_resp.status_code == 200
    # Check the <html lang> attribute specifically, not hreflang alternate link tags
    assert '<html lang="el"' in gr_resp.text
    assert '<html lang="el"' not in cy_resp.text
