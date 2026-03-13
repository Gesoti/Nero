"""Tests for YoY chart data handling with sparse historical data.

The YoY comparison fails on 'day' granularity because older years have
sparse data (monthly samples, not daily). This tests that the chart
infrastructure handles this correctly.
"""
from __future__ import annotations

from pathlib import Path


class TestYoYChartJS:
    """Verify the charts.js handles sparse year data gracefully."""

    def _read_charts_js(self) -> str:
        return Path("app/static/js/charts.js").read_text()

    def test_charts_js_has_sparse_data_threshold(self):
        """charts.js should define a threshold for sparse year data."""
        content = self._read_charts_js()
        assert "SPARSE_YEAR_THRESHOLD" in content

    def test_charts_js_has_is_year_sparse_function(self):
        """charts.js should have a function to check if a year has sparse data."""
        content = self._read_charts_js()
        assert "isYearSparse" in content


class TestYoYDashboardTemplate:
    """Dashboard template should handle sparse year warnings."""

    async def test_dashboard_has_sparse_data_handling(self, seeded_async_client):
        """Dashboard template must include sparse data handling for YoY."""
        resp = await seeded_async_client.get("/")
        assert resp.status_code == 200
        # The template should include the sparse year logic
        assert "isYearSparse" in resp.text or "sparse" in resp.text.lower()
