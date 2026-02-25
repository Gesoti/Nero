"""
Integration tests for app/routes/pages.py.
Uses async_client (httpx.ASGITransport) with an in-memory SQLite DB.
The lifespan is NOT triggered — no APScheduler, no upstream API calls.
"""
from __future__ import annotations

import pytest


class TestDashboardRoute:
    async def test_dashboard_returns_200(self, async_client):
        response = await async_client.get("/")
        assert response.status_code == 200

    async def test_dashboard_contains_nero_brand(self, async_client):
        response = await async_client.get("/")
        assert "Nero" in response.text

    async def test_dashboard_title_uses_nero(self, async_client):
        r = await async_client.get("/")
        assert "<title>Nero" in r.text

    async def test_no_old_branding_in_dashboard(self, async_client):
        r = await async_client.get("/")
        assert "Cyprus Water Levels" not in r.text
        assert "CyprusWater" not in r.text

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client):
        r = await async_client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "content-security-policy" in r.headers
        assert "content-security-policy-report-only" not in r.headers


class TestMapRoute:
    async def test_map_returns_200(self, async_client):
        response = await async_client.get("/map")
        assert response.status_code == 200

    async def test_map_contains_leaflet(self, async_client):
        response = await async_client.get("/map")
        assert "leaflet" in response.text.lower()


class TestAboutRoute:
    async def test_about_returns_200(self, async_client):
        response = await async_client.get("/about")
        assert response.status_code == 200


class TestDamDetailRoute:
    async def test_nonexistent_dam_returns_404(self, async_client):
        response = await async_client.get("/dam/nonexistent-dam-xyz")
        assert response.status_code == 404


class TestPrivacyRoute:
    @pytest.mark.asyncio
    async def test_privacy_returns_200(self, async_client):
        r = await async_client.get("/privacy")
        assert r.status_code == 200


class TestScriptLoading:
    async def test_cdn_scripts_are_deferred(self, async_client):
        import re
        r = await async_client.get("/")
        cdn_scripts = re.findall(r'<script[^>]+src="https://cdn[^"]+[^>]*>', r.text)
        assert len(cdn_scripts) >= 2, "Expected at least 2 CDN scripts"
        for tag in cdn_scripts:
            assert 'defer' in tag, f"CDN script missing defer: {tag}"


class TestSEOMetaTags:
    async def test_dashboard_has_meta_description(self, async_client):
        r = await async_client.get("/")
        assert '<meta name="description"' in r.text

    async def test_dashboard_has_og_title(self, async_client):
        r = await async_client.get("/")
        assert '<meta property="og:title"' in r.text

    async def test_dashboard_has_og_description(self, async_client):
        r = await async_client.get("/")
        assert '<meta property="og:description"' in r.text

    async def test_dashboard_has_og_type(self, async_client):
        r = await async_client.get("/")
        assert '<meta property="og:type"' in r.text

    async def test_about_has_meta_description(self, async_client):
        r = await async_client.get("/about")
        assert '<meta name="description"' in r.text

    async def test_map_has_meta_description(self, async_client):
        r = await async_client.get("/map")
        assert '<meta name="description"' in r.text


class TestDamDetailMeta:
    async def test_dam_detail_has_specific_meta_description(self, seeded_async_client):
        r = await seeded_async_client.get("/dam/Kouris")
        assert r.status_code == 200
        assert "Kouris" in r.text
        # Should contain a dam-specific meta description, not the default
        assert '<meta name="description" content="Kouris' in r.text

    async def test_dam_detail_has_og_title_with_dam_name(self, seeded_async_client):
        r = await seeded_async_client.get("/dam/Kouris")
        assert 'og:title" content="Kouris' in r.text
        assert "Nero" in r.text

    async def test_dam_detail_title_uses_nero(self, seeded_async_client):
        r = await seeded_async_client.get("/dam/Kouris")
        assert "Nero" in r.text
        assert "Cyprus Water Levels" not in r.text


class TestRobotsTxt:
    async def test_robots_returns_200_text(self, async_client):
        r = await async_client.get("/robots.txt")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    async def test_robots_contains_sitemap(self, async_client):
        r = await async_client.get("/robots.txt")
        assert "Sitemap:" in r.text
        assert "nero.cy/sitemap.xml" in r.text

    async def test_robots_allows_all(self, async_client):
        r = await async_client.get("/robots.txt")
        assert "User-agent: *" in r.text
        assert "Disallow:" in r.text


class TestAdsTxt:
    async def test_ads_txt_returns_200_text(self, async_client):
        r = await async_client.get("/ads.txt")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    async def test_ads_txt_contains_google_entry(self, async_client):
        r = await async_client.get("/ads.txt")
        assert "google.com, pub-3066658032903900, DIRECT, f08c47fec0942fa0" in r.text


class TestSitemapXml:
    async def test_sitemap_returns_200_xml(self, async_client):
        r = await async_client.get("/sitemap.xml")
        assert r.status_code == 200
        assert "xml" in r.headers["content-type"]

    async def test_sitemap_contains_static_urls(self, async_client):
        r = await async_client.get("/sitemap.xml")
        assert "<loc>" in r.text
        # Should contain main pages with correct domain
        for path in ["/", "/map", "/about"]:
            assert f"nero.cy{path}" in r.text

    async def test_sitemap_contains_dam_urls(self, seeded_async_client):
        r = await seeded_async_client.get("/sitemap.xml")
        assert "/dam/Kouris" in r.text


class TestBlogRoutes:
    async def test_blog_index_returns_200(self, async_client):
        r = await async_client.get("/blog")
        assert r.status_code == 200

    async def test_blog_index_contains_nero_title(self, async_client):
        r = await async_client.get("/blog")
        assert "Nero" in r.text
        assert "Blog" in r.text

    async def test_blog_nav_link_present(self, async_client):
        r = await async_client.get("/")
        assert 'href="/blog"' in r.text


class TestHealthRoute:
    async def test_health_returns_200_json(self, async_client):
        r = await async_client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"

    async def test_health_does_not_expose_last_sync(self, async_client):
        r = await async_client.get("/health")
        body = r.json()
        assert "last_sync" not in body
