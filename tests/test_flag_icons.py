"""Tests for flag-icons CSS library and flag display in country dropdown."""
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
async def multi_country_client(in_memory_db):
    """Client with cy,gr,es enabled and CY data seeded."""
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


class TestFlagIconsCSS:
    """flag-icons CSS must be loaded in the HTML head."""

    async def test_flag_icons_link_present_in_head(self, multi_country_client):
        """Base template head must include the flag-icons stylesheet link."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert "flag-icons" in resp.text

    async def test_flag_icons_cdn_url_correct(self, multi_country_client):
        """The flag-icons link must point to the correct jsDelivr CDN URL."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert "cdn.jsdelivr.net/gh/lipis/flag-icons@7.2.3/css/flag-icons.min.css" in resp.text

    async def test_flag_icons_has_integrity_attribute(self, multi_country_client):
        """The flag-icons link must include a sha384 integrity attribute."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert 'integrity="sha384-' in resp.text


class TestCountryDropdownFlags:
    """Country flags must appear in the navbar country switcher dropdown."""

    async def test_cyprus_flag_in_toggle_button(self, multi_country_client):
        """Cyprus page toggle button must include fi fi-cy flag class."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert "fi fi-cy" in resp.text

    async def test_greece_flag_in_dropdown(self, multi_country_client):
        """Country dropdown must include fi fi-gr flag class for Greece."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert "fi fi-gr" in resp.text

    async def test_spain_flag_in_dropdown(self, multi_country_client):
        """Country dropdown must include fi fi-es flag class for Spain."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        assert "fi fi-es" in resp.text

    async def test_flag_span_has_aria_hidden(self, multi_country_client):
        """Flag spans must have aria-hidden='true' for accessibility."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        # The flag spans have aria-hidden="true"
        assert 'aria-hidden="true"' in resp.text

    async def test_dropdown_items_use_flex_layout(self, multi_country_client):
        """Dropdown items must use flex layout to align flag and label."""
        resp = await multi_country_client.get("/")
        assert resp.status_code == 200
        # items use flex items-center gap-2
        assert "flex items-center gap-2" in resp.text
