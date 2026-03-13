"""Tests for revised About page — multi-country, no tech stack details."""
from __future__ import annotations


class TestAboutPage:
    async def test_about_returns_200(self, seeded_async_client):
        resp = await seeded_async_client.get("/about")
        assert resp.status_code == 200

    async def test_about_mentions_multiple_countries(self, seeded_async_client):
        """About page should reference the multi-country nature of the project."""
        resp = await seeded_async_client.get("/about")
        assert resp.status_code == 200
        text = resp.text
        # Should mention monitoring water levels across countries, not just Cyprus
        assert "Greece" in text or "countries" in text.lower()

    async def test_about_does_not_mention_tech_stack_in_content(self, seeded_async_client):
        """About page prose should not expose implementation details to users."""
        resp = await seeded_async_client.get("/about")
        assert resp.status_code == 200
        # Check only the visible article text, not CDN script tags in <head>
        # Extract text between the content block markers
        text = resp.text.lower()
        assert "built with python" not in text
        assert "fastapi" not in text
        assert "jinja2" not in text

    async def test_about_does_not_say_over_130_tests(self, seeded_async_client):
        """About page should not reference test count (outdated, irrelevant to users)."""
        resp = await seeded_async_client.get("/about")
        assert resp.status_code == 200
        assert "130 automated tests" not in resp.text
        assert "test-driven" not in resp.text.lower()
