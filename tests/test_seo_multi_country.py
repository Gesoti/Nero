"""
Tests for G12: unified sitemap and hreflang cross-links for multi-country SEO.

These tests use seeded_async_client (CY only) and verify:
- Sitemap always includes CY root URL
- Sitemap includes GR root and Mornos dam when gr is enabled
  (Greece dam names must be hardcoded in the handler — gr DB won't be seeded)
- hreflang links are present on both CY and GR pages
"""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from unittest.mock import patch
from app.config import settings
from app.main import app
from app.middleware.country import CountryPrefixMiddleware
from tests.conftest import _DamStub, _SnapshotStub


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def gr_enabled_client(in_memory_db):
    """Client with gr enabled but only CY data seeded (tests gr URL generation without gr DB)."""
    from app.db import upsert_dams, upsert_percentage_snapshot

    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ── Sitemap tests ─────────────────────────────────────────────────────────────


async def test_sitemap_includes_cy_root(seeded_async_client: httpx.AsyncClient) -> None:
    """Sitemap must always contain the Cyprus root URL."""
    resp = await seeded_async_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "https://nero.cy/" in resp.text


async def test_sitemap_includes_gr_root(gr_enabled_client: httpx.AsyncClient) -> None:
    """When gr is enabled, sitemap must include /gr/ even if gr DB is not seeded."""
    resp = await gr_enabled_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/gr/" in resp.text


async def test_sitemap_includes_gr_dam_mornos(gr_enabled_client: httpx.AsyncClient) -> None:
    """When gr is enabled, sitemap must include /gr/dam/Mornos (hardcoded from provider)."""
    resp = await gr_enabled_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/gr/dam/Mornos" in resp.text


# ── hreflang tests ────────────────────────────────────────────────────────────


async def test_hreflang_cy_page_links_to_gr(gr_enabled_client: httpx.AsyncClient) -> None:
    """Cyprus / must include hreflang pointing toward the /gr/ equivalent."""
    resp = await gr_enabled_client.get("/")
    assert resp.status_code == 200
    # Both countries use "en" locale now; verify GR alternate link exists
    assert "/gr/" in resp.text


async def test_hreflang_gr_page_links_to_cy(gr_enabled_client: httpx.AsyncClient) -> None:
    """Greece /gr/ must include hreflang=en pointing toward the CY equivalent."""
    resp = await gr_enabled_client.get("/gr/")
    assert resp.status_code == 200
    assert 'hreflang="en"' in resp.text


# ── Three-country hreflang/sitemap tests ─────────────────────────────────────


@pytest_asyncio.fixture
async def three_country_client(in_memory_db):
    """Client with cy,gr,es all enabled."""
    from app.db import upsert_dams, upsert_percentage_snapshot

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


async def test_sitemap_includes_es_root(three_country_client: httpx.AsyncClient) -> None:
    """Sitemap must include /es/ when Spain is enabled."""
    resp = await three_country_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/es/" in resp.text


async def test_sitemap_includes_es_dam_la_serena(three_country_client: httpx.AsyncClient) -> None:
    """Sitemap must include /es/dam/La%20Serena from static metadata."""
    resp = await three_country_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/es/dam/La%20Serena" in resp.text


async def test_hreflang_cy_page_links_to_es(three_country_client: httpx.AsyncClient) -> None:
    """CY dashboard must include hreflang link to /es/."""
    resp = await three_country_client.get("/")
    assert resp.status_code == 200
    assert "/es/" in resp.text


async def test_hreflang_es_page_links_to_cy_and_gr(three_country_client: httpx.AsyncClient) -> None:
    """Spain /es/ must include hreflang links to both CY and GR."""
    resp = await three_country_client.get("/es/")
    assert resp.status_code == 200
    assert 'hreflang="en"' in resp.text
    assert "/gr/" in resp.text


# ── Four-country hreflang/sitemap tests (with Portugal) ──────────────────


@pytest_asyncio.fixture
async def four_country_client(in_memory_db):
    """Client with cy,gr,es,pt all enabled."""
    from app.db import upsert_dams, upsert_percentage_snapshot

    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())

    with patch.object(settings, "enabled_countries", "cy,gr,es,pt"):
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=["cy", "gr", "es", "pt"],
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_sitemap_includes_pt_root(four_country_client: httpx.AsyncClient) -> None:
    """Sitemap must include /pt/ when Portugal is enabled."""
    resp = await four_country_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/pt/" in resp.text


async def test_sitemap_includes_pt_dam_alqueva(four_country_client: httpx.AsyncClient) -> None:
    """Sitemap must include /pt/dam/Alqueva from static metadata."""
    resp = await four_country_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/pt/dam/Alqueva" in resp.text


async def test_hreflang_cy_page_links_to_pt(four_country_client: httpx.AsyncClient) -> None:
    """CY dashboard must include hreflang link to /pt/."""
    resp = await four_country_client.get("/")
    assert resp.status_code == 200
    assert "/pt/" in resp.text


async def test_hreflang_pt_page_links_to_cy_and_gr_and_es(four_country_client: httpx.AsyncClient) -> None:
    """Portugal /pt/ must include hreflang links to CY, GR, and ES."""
    resp = await four_country_client.get("/pt/")
    assert resp.status_code == 200
    assert 'hreflang="en"' in resp.text
    assert "/gr/" in resp.text
    assert "/es/" in resp.text
