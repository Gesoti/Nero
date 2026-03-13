"""
Tests for G8: parameterised map page per country.

These tests verify that the map page renders with the correct centre
coordinates for each country. The map centre is passed from
COUNTRY_MAP_CENTRES in the route handler, not hardcoded in the template.
"""
from __future__ import annotations

import httpx
import pytest_asyncio

from unittest.mock import patch
from app.config import settings
from app.main import app
from app.middleware.country import CountryPrefixMiddleware
from tests.conftest import _DamStub, _SnapshotStub


@pytest_asyncio.fixture
async def gr_seeded_map_client(in_memory_db):
    """gr_client with dam + percentage pre-seeded for map route tests."""
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


async def test_map_page_cy_has_cyprus_centre(seeded_async_client: httpx.AsyncClient) -> None:
    """Cyprus map page must contain the CY centre latitude (~34.917)."""
    resp = await seeded_async_client.get("/map")
    assert resp.status_code == 200
    # COUNTRY_MAP_CENTRES["cy"] = (34.917, 33.0)
    assert "34.917" in resp.text


async def test_map_page_cy_has_cyprus_lng(seeded_async_client: httpx.AsyncClient) -> None:
    """Cyprus map page must contain the CY centre longitude (33.0)."""
    resp = await seeded_async_client.get("/map")
    assert resp.status_code == 200
    assert "33.0" in resp.text


async def test_map_page_gr_has_greece_centre(gr_seeded_map_client: httpx.AsyncClient) -> None:
    """Greece map page must contain the GR centre latitude (~38.5)."""
    resp = await gr_seeded_map_client.get("/gr/map")
    assert resp.status_code == 200
    # COUNTRY_MAP_CENTRES["gr"] = (38.5, 22.5)
    assert "38.5" in resp.text


async def test_map_page_gr_has_greece_lng(gr_seeded_map_client: httpx.AsyncClient) -> None:
    """Greece map page must contain the GR centre longitude (22.5)."""
    resp = await gr_seeded_map_client.get("/gr/map")
    assert resp.status_code == 200
    assert "22.5" in resp.text


async def test_map_page_cy_does_not_have_greece_centre(seeded_async_client: httpx.AsyncClient) -> None:
    """Cyprus map must not use the Greece centre lat 38.5."""
    resp = await seeded_async_client.get("/map")
    assert resp.status_code == 200
    assert "38.5" not in resp.text
