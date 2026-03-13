"""Tests for country navigation menu in base template."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest_asyncio

from app.config import settings
from app.db import upsert_dams, upsert_percentage_snapshot
from app.main import app
from app.middleware.country import CountryPrefixMiddleware
from tests.conftest import _DamStub, _SnapshotStub


@pytest_asyncio.fixture
async def gr_enabled_seeded_client(in_memory_db):
    """Client with cy,gr enabled and CY data seeded."""
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


class TestCountryNavigation:
    """Country navigation should be visible when multiple countries are enabled."""

    async def test_nav_has_country_nav_element(self, gr_enabled_seeded_client):
        """Nav must contain a country-nav element when multiple countries enabled."""
        resp = await gr_enabled_seeded_client.get("/")
        assert resp.status_code == 200
        assert 'id="country-nav"' in resp.text

    async def test_nav_has_greece_link_in_country_nav(self, gr_enabled_seeded_client):
        """Country nav must have a link to Greece (/gr/)."""
        resp = await gr_enabled_seeded_client.get("/")
        assert resp.status_code == 200
        # The country nav should contain both country links
        assert 'href="/gr/"' in resp.text or "href=\"/gr/\"" in resp.text

    async def test_gr_page_has_cyprus_link_in_nav(self, gr_enabled_seeded_client):
        """Greece pages should have a link to Cyprus in the country nav."""
        resp = await gr_enabled_seeded_client.get("/gr/")
        assert resp.status_code == 200
        assert 'href="/"' in resp.text

    async def test_cy_page_marks_cyprus_as_active(self, gr_enabled_seeded_client):
        """Cyprus page should mark Cyprus as the active country."""
        resp = await gr_enabled_seeded_client.get("/")
        assert resp.status_code == 200
        assert 'data-active="cy"' in resp.text

    async def test_gr_page_marks_greece_as_active(self, gr_enabled_seeded_client):
        """Greece page should mark Greece as the active country."""
        resp = await gr_enabled_seeded_client.get("/gr/")
        assert resp.status_code == 200
        assert 'data-active="gr"' in resp.text

    async def test_single_country_no_nav(self, seeded_async_client):
        """When only one country is enabled, no country nav should appear."""
        resp = await seeded_async_client.get("/")
        assert resp.status_code == 200
        assert 'id="country-nav"' not in resp.text

    async def test_country_labels_in_template(self, gr_enabled_seeded_client):
        """Template context must include country labels for nav rendering."""
        resp = await gr_enabled_seeded_client.get("/")
        assert resp.status_code == 200
        # Check for human-readable country names in the nav area
        text = resp.text
        assert "Cyprus" in text
        assert "Greece" in text
