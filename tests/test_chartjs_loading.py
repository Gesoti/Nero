"""
Tests verifying that Chart.js scripts are loaded ONLY on pages that use charts
(dashboard, dam_detail) and NOT on pages that don't (about, map, privacy, blog).

This prevents unnecessary bandwidth usage on pages that never render charts.
"""
from __future__ import annotations

CHARTJS_CDN = "chart.js"
CHARTJS_ADAPTER = "chartjs-adapter-date-fns"
CHARTS_JS = "/static/js/charts.js"


class TestChartJsNotLoadedOnStaticPages:
    """Chart.js should not appear on pages that have no charts."""

    async def test_about_page_has_no_chartjs(self, async_client):
        r = await async_client.get("/about")
        assert r.status_code == 200
        assert CHARTJS_CDN not in r.text
        assert CHARTJS_ADAPTER not in r.text
        assert CHARTS_JS not in r.text

    async def test_map_page_has_no_chartjs(self, async_client):
        r = await async_client.get("/map")
        assert r.status_code == 200
        assert CHARTJS_CDN not in r.text
        assert CHARTJS_ADAPTER not in r.text
        assert CHARTS_JS not in r.text

    async def test_privacy_page_has_no_chartjs(self, async_client):
        r = await async_client.get("/privacy")
        assert r.status_code == 200
        assert CHARTJS_CDN not in r.text
        assert CHARTJS_ADAPTER not in r.text
        assert CHARTS_JS not in r.text

    async def test_blog_index_has_no_chartjs(self, async_client):
        r = await async_client.get("/blog")
        assert r.status_code == 200
        assert CHARTJS_CDN not in r.text
        assert CHARTJS_ADAPTER not in r.text
        assert CHARTS_JS not in r.text


class TestChartJsLoadedOnChartPages:
    """Chart.js must be present on pages that render charts."""

    async def test_dashboard_has_chartjs(self, async_client):
        r = await async_client.get("/")
        assert r.status_code == 200
        assert CHARTJS_CDN in r.text
        assert CHARTJS_ADAPTER in r.text
        assert CHARTS_JS in r.text

    async def test_dam_detail_has_chartjs(self, seeded_async_client):
        r = await seeded_async_client.get("/dam/Kouris")
        assert r.status_code == 200
        assert CHARTJS_CDN in r.text
        assert CHARTJS_ADAPTER in r.text
        assert CHARTS_JS in r.text
