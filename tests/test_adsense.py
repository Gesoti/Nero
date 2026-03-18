"""
Tests for AdSense integration: CSP nonce generation, publisher ID,
and privacy policy domain references.
"""
from __future__ import annotations

import re

import pytest


class TestCSPNonce:
    """CSP header must contain a per-request nonce for AdSense compatibility."""

    @pytest.mark.asyncio
    async def test_csp_contains_nonce(self, async_client):
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert re.search(r"'nonce-[A-Za-z0-9_-]+'", csp), (
            f"CSP should contain a nonce directive, got: {csp}"
        )

    @pytest.mark.asyncio
    async def test_nonce_differs_per_request(self, async_client):
        r1 = await async_client.get("/")
        r2 = await async_client.get("/")
        csp1 = r1.headers.get("content-security-policy", "")
        csp2 = r2.headers.get("content-security-policy", "")
        nonce1 = re.search(r"'nonce-([A-Za-z0-9_-]+)'", csp1)
        nonce2 = re.search(r"'nonce-([A-Za-z0-9_-]+)'", csp2)
        assert nonce1 and nonce2, "Both requests should have nonces"
        assert nonce1.group(1) != nonce2.group(1), "Nonces must differ per request"

    @pytest.mark.asyncio
    async def test_csp_allows_adsense_frames(self, async_client):
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert "googleads.g.doubleclick.net" in csp, "CSP must allow AdSense frames"
        assert "tpc.googlesyndication.com" in csp, "CSP must allow AdSense frames"

    @pytest.mark.asyncio
    async def test_csp_allows_https_scripts(self, async_client):
        """AdSense needs 'strict-dynamic' or https: in script-src."""
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert "https:" in csp or "'strict-dynamic'" in csp, (
            "CSP script-src must allow https: or strict-dynamic for AdSense"
        )

    @pytest.mark.asyncio
    async def test_csp_allows_https_connect(self, async_client):
        """AdSense needs connect-src to allow https:."""
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert "connect-src" in csp
        # Extract connect-src directive value
        connect_match = re.search(r"connect-src\s+([^;]+)", csp)
        assert connect_match, "connect-src directive must exist"
        assert "https:" in connect_match.group(1), "connect-src must allow https:"


class TestAdSensePublisherID:
    """Publisher ID is driven by WL_ADSENSE_PUB_ID env var; absent means no ads."""

    @pytest.mark.asyncio
    async def test_base_template_no_publisher_id_when_unconfigured(self, async_client):
        r = await async_client.get("/")
        assert "ca-pub-XXXXXXXXXXXXXXXXXX" not in r.text, (
            "Dashboard should NOT contain placeholder publisher ID"
        )

    @pytest.mark.asyncio
    async def test_dashboard_no_ad_script_when_unconfigured(self, async_client):
        r = await async_client.get("/")
        ad_slots = re.findall(r'data-ad-client="([^"]+)"', r.text)
        assert ad_slots == [], (
            "No ad-client attrs expected when adsense_pub_id is not configured"
        )

    @pytest.mark.asyncio
    async def test_dashboard_shows_publisher_id_when_configured(self, async_client, monkeypatch):
        import app.routes.pages as pages_mod
        from app.config import Settings
        monkeypatch.setattr(pages_mod, "settings", Settings(adsense_pub_id="ca-pub-test123"))
        r = await async_client.get("/")
        assert "ca-pub-test123" in r.text, (
            "Dashboard should render configured publisher ID"
        )

    @pytest.mark.asyncio
    async def test_dam_detail_no_ad_unit_when_unconfigured(self, seeded_async_client):
        r = await seeded_async_client.get("/dam/Kouris")
        assert r.status_code == 200
        ad_slots = re.findall(r'data-ad-client="([^"]+)"', r.text)
        assert ad_slots == [], (
            "No ad-client attrs expected on dam detail when adsense_pub_id is not configured"
        )


class TestCSPNonceOnTags:
    """All <script> and <style> tags in HTML must carry the CSP nonce attribute."""

    @pytest.mark.asyncio
    async def test_all_scripts_have_nonce_on_dashboard(self, async_client):
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        nonce_match = re.search(r"'nonce-([A-Za-z0-9_-]+)'", csp)
        assert nonce_match, "CSP must contain a nonce"
        nonce = nonce_match.group(1)
        # Every <script> tag must carry the nonce
        scripts = re.findall(r"<script[^>]*>", r.text)
        for tag in scripts:
            assert f'nonce="{nonce}"' in tag, (
                f"Script tag missing nonce: {tag[:120]}"
            )

    @pytest.mark.asyncio
    async def test_all_scripts_have_nonce_on_map(self, async_client):
        r = await async_client.get("/map")
        csp = r.headers.get("content-security-policy", "")
        nonce_match = re.search(r"'nonce-([A-Za-z0-9_-]+)'", csp)
        assert nonce_match
        nonce = nonce_match.group(1)
        scripts = re.findall(r"<script[^>]*>", r.text)
        for tag in scripts:
            assert f'nonce="{nonce}"' in tag, (
                f"Script tag missing nonce on /map: {tag[:120]}"
            )

    @pytest.mark.asyncio
    async def test_style_src_allows_self_and_cdn(self, async_client):
        """style-src must allow 'self' and CDN stylesheets (no nonce needed)."""
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        style_match = re.search(r"style-src\s+([^;]+)", csp)
        assert style_match, "style-src directive must exist"
        style_src = style_match.group(1)
        assert "'self'" in style_src, "style-src must include 'self'"
        assert "cdn.jsdelivr.net" in style_src, "style-src must allow CDN"

    @pytest.mark.asyncio
    async def test_style_src_has_no_nonce(self, async_client):
        """style-src must NOT use nonces (so 'unsafe-inline' remains effective)."""
        r = await async_client.get("/")
        csp = r.headers.get("content-security-policy", "")
        style_match = re.search(r"style-src\s+([^;]+)", csp)
        assert style_match, "style-src directive must exist"
        style_src = style_match.group(1)
        assert "nonce-" not in style_src, (
            "style-src must not contain nonce (it disables 'unsafe-inline')"
        )


class TestPrivacyPolicyDomain:
    """Privacy policy must reference nero.cy, not cypruswater.com."""

    @pytest.mark.asyncio
    async def test_privacy_references_nero_cy(self, async_client):
        r = await async_client.get("/privacy")
        assert "nero.cy" in r.text, "Privacy policy should reference nero.cy domain"

    @pytest.mark.asyncio
    async def test_privacy_no_cypruswater_domain(self, async_client):
        r = await async_client.get("/privacy")
        assert "cypruswater.com" not in r.text, (
            "Privacy policy should NOT reference cypruswater.com"
        )
