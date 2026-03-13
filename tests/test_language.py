"""Tests for language middleware and hreflang tags (B8)."""
from __future__ import annotations


class TestLanguageMiddleware:
    async def test_default_locale_set_on_request(self, async_client):
        """Requests without /en/ prefix should have locale set to default."""
        r = await async_client.get("/")
        assert r.status_code == 200
        # The locale should be reflected in the HTML lang attribute
        assert 'lang="en"' in r.text

    async def test_hreflang_tag_in_html(self, async_client):
        """Pages should include hreflang link tags for SEO."""
        r = await async_client.get("/")
        assert 'hreflang=' in r.text

    async def test_hreflang_self_reference(self, async_client):
        """Pages should have an x-default hreflang."""
        r = await async_client.get("/")
        assert 'hreflang="x-default"' in r.text
