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

    async def test_dashboard_contains_cyprus(self, async_client):
        response = await async_client.get("/")
        assert "Cyprus" in response.text

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client):
        r = await async_client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "content-security-policy-report-only" in r.headers


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


class TestHealthRoute:
    async def test_health_returns_200_json(self, async_client):
        r = await async_client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "last_sync" in body
