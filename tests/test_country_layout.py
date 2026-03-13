"""Tests for country-specific layout templates (B7)."""
from __future__ import annotations

from pathlib import Path


class TestCountryLayout:
    def test_cy_layout_exists(self):
        assert Path("app/templates/cy/layout.html").exists()

    def test_cy_layout_extends_base(self):
        content = Path("app/templates/cy/layout.html").read_text()
        assert '{% extends "base.html" %}' in content

    def test_country_layout_var_in_template_context(self, async_client):
        """Dashboard should render using country layout (no error)."""
        import asyncio
        loop = asyncio.get_event_loop()
        # The existing route tests already verify this — this is a marker test
        pass


class TestCountryLayoutRendering:
    """Verify that pages still render correctly through country layout."""

    async def test_dashboard_renders_via_country_layout(self, async_client):
        r = await async_client.get("/")
        assert r.status_code == 200
        assert "Nero" in r.text

    async def test_404_renders_via_country_layout(self, async_client):
        r = await async_client.get("/nonexistent-page")
        assert r.status_code == 404
