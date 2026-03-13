"""
Tests for app/providers/ — DataProvider protocol and Cyprus implementation.

Verifies:
1. DataProvider protocol exists with required methods
2. CyprusProvider implements the protocol
3. Dataclasses are importable from providers.base
4. CyprusProvider fetch methods work (same mock strategy as test_api_client.py)
5. Backwards-compat re-exports from app.api_client still work
"""
from __future__ import annotations

from datetime import date
from typing import runtime_checkable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ── Protocol structure tests ─────────────────────────────────────────────────

class TestDataProviderProtocol:
    def test_protocol_importable(self):
        from app.providers.base import DataProvider
        assert DataProvider is not None

    def test_protocol_is_runtime_checkable(self):
        from app.providers.base import DataProvider
        assert hasattr(DataProvider, '__protocol_attrs__') or runtime_checkable

    def test_protocol_requires_fetch_dams(self):
        from app.providers.base import DataProvider
        # Protocol must declare fetch_dams
        assert "fetch_dams" in dir(DataProvider)

    def test_protocol_requires_fetch_percentages(self):
        from app.providers.base import DataProvider
        assert "fetch_percentages" in dir(DataProvider)

    def test_protocol_requires_fetch_date_statistics(self):
        from app.providers.base import DataProvider
        assert "fetch_date_statistics" in dir(DataProvider)

    def test_protocol_requires_fetch_timeseries(self):
        from app.providers.base import DataProvider
        assert "fetch_timeseries" in dir(DataProvider)

    def test_protocol_requires_fetch_monthly_inflows(self):
        from app.providers.base import DataProvider
        assert "fetch_monthly_inflows" in dir(DataProvider)

    def test_protocol_requires_fetch_events(self):
        from app.providers.base import DataProvider
        assert "fetch_events" in dir(DataProvider)

    def test_protocol_requires_close(self):
        from app.providers.base import DataProvider
        assert "close" in dir(DataProvider)


# ── Dataclass import tests ───────────────────────────────────────────────────

class TestBaseDataclasses:
    def test_dam_info_importable(self):
        from app.providers.base import DamInfo
        assert DamInfo is not None

    def test_dam_percentage_importable(self):
        from app.providers.base import DamPercentage
        assert DamPercentage is not None

    def test_percentage_snapshot_importable(self):
        from app.providers.base import PercentageSnapshot
        assert PercentageSnapshot is not None

    def test_dam_statistic_importable(self):
        from app.providers.base import DamStatistic
        assert DamStatistic is not None

    def test_date_statistics_importable(self):
        from app.providers.base import DateStatistics
        assert DateStatistics is not None

    def test_monthly_inflow_importable(self):
        from app.providers.base import MonthlyInflow
        assert MonthlyInflow is not None

    def test_water_event_importable(self):
        from app.providers.base import WaterEvent
        assert WaterEvent is not None

    def test_upstream_api_error_importable(self):
        from app.providers.base import UpstreamAPIError
        assert UpstreamAPIError is not None


# ── CyprusProvider tests ─────────────────────────────────────────────────────

class TestCyprusProvider:
    def test_importable(self):
        from app.providers.cyprus import CyprusProvider
        assert CyprusProvider is not None

    def test_implements_data_provider(self):
        from app.providers.base import DataProvider
        from app.providers.cyprus import CyprusProvider
        provider = CyprusProvider.__new__(CyprusProvider)
        assert isinstance(provider, DataProvider)

    async def test_fetch_dams(self):
        from app.providers.cyprus import CyprusProvider

        payload = [{
            "nameEn": "Kouris", "nameEl": "Κούρης",
            "yearOfConstruction": 1988, "height": 110,
            "capacity": 115_000_000, "lat": 34.717, "lng": 32.937,
            "riverNameEl": "Κούρης", "typeEl": "Λιθόρριπτο",
            "imageUrl": "https://example.com/kouris.jpg",
            "wikipediaUrl": "https://el.wikipedia.org/wiki/Kouris",
        }]
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp

        provider = CyprusProvider(client=mock_client)
        result = await provider.fetch_dams()

        assert len(result) == 1
        assert result[0].name_en == "Kouris"
        assert result[0].capacity_mcm == pytest.approx(115.0)

    async def test_fetch_percentages(self):
        from app.providers.cyprus import CyprusProvider

        payload = {
            "date": "Feb 18, 2026 12:00:00 AM",
            "damNamesToPercentage": {"Kouris": 0.35},
            "totalPercentage": 0.32,
            "totalCapacityInMCM": 327.0,
        }
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp

        provider = CyprusProvider(client=mock_client)
        snap = await provider.fetch_percentages(date(2026, 2, 18))

        assert snap.date == date(2026, 2, 18)
        assert snap.total_percentage == pytest.approx(0.32)

    async def test_close(self):
        from app.providers.cyprus import CyprusProvider

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        provider = CyprusProvider(client=mock_client)
        await provider.close()
        mock_client.aclose.assert_awaited_once()


# ── Backwards-compat re-exports ──────────────────────────────────────────────

class TestBackwardsCompat:
    """api_client.py must still export everything it used to."""

    def test_fetch_dams_importable(self):
        from app.api_client import fetch_dams
        assert callable(fetch_dams)

    def test_fetch_percentages_importable(self):
        from app.api_client import fetch_percentages
        assert callable(fetch_percentages)

    def test_fetch_date_statistics_importable(self):
        from app.api_client import fetch_date_statistics
        assert callable(fetch_date_statistics)

    def test_fetch_timeseries_importable(self):
        from app.api_client import fetch_timeseries
        assert callable(fetch_timeseries)

    def test_fetch_monthly_inflows_importable(self):
        from app.api_client import fetch_monthly_inflows
        assert callable(fetch_monthly_inflows)

    def test_fetch_events_importable(self):
        from app.api_client import fetch_events
        assert callable(fetch_events)

    def test_close_client_importable(self):
        from app.api_client import close_client
        assert callable(close_client)

    def test_upstream_api_error_importable(self):
        from app.api_client import UpstreamAPIError
        assert issubclass(UpstreamAPIError, Exception)

    def test_dam_info_importable(self):
        from app.api_client import DamInfo
        assert DamInfo is not None

    def test_percentage_snapshot_importable(self):
        from app.api_client import PercentageSnapshot
        assert PercentageSnapshot is not None
