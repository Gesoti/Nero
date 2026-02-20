"""
Unit tests for app/api_client.py.

Strategy: patch `app.api_client._get_client` to return a mock httpx.AsyncClient
so no real network calls are made. Each test configures mock response JSON that
matches the shapes documented in api_client.py's module docstring.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api_client import (
    UpstreamAPIError,
    fetch_dams,
    fetch_percentages,
    fetch_date_statistics,
    fetch_monthly_inflows,
    fetch_events,
    fetch_timeseries,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    """
    Build a synchronous MagicMock that behaves like an httpx.Response.
    raise_for_status() does nothing on 2xx and raises HTTPStatusError on 4xx/5xx.
    """
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data

    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_resp,
        )
    else:
        mock_resp.raise_for_status.return_value = None

    return mock_resp


def _make_mock_client(json_data: object, status_code: int = 200) -> AsyncMock:
    """Return a mock httpx.AsyncClient whose .get() returns the given response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _make_mock_response(json_data, status_code)
    return mock_client


# ── fetch_dams ────────────────────────────────────────────────────────────────

class TestFetchDams:
    # Minimal valid /dams payload (one dam)
    _DAMS_PAYLOAD = [
        {
            "nameEn": "Kouris",
            "nameEl": "Κούρης",
            "yearOfConstruction": 1988,
            "height": 110,
            "capacity": 115_000_000,  # m3
            "lat": 34.717,
            "lng": 32.937,
            "riverNameEl": "Κούρης",
            "typeEl": "Λιθόρριπτο",
            "imageUrl": "https://example.com/kouris.jpg",
            "wikipediaUrl": "https://el.wikipedia.org/wiki/Kouris",
        }
    ]

    async def test_returns_list_of_dam_info(self):
        mock_client = _make_mock_client(self._DAMS_PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            result = await fetch_dams()

        assert len(result) == 1
        dam = result[0]
        assert dam.name_en == "Kouris"
        assert dam.name_el == "Κούρης"
        assert dam.capacity_m3 == 115_000_000
        assert dam.capacity_mcm == pytest.approx(115.0)
        assert dam.lat == pytest.approx(34.717)
        assert dam.lng == pytest.approx(32.937)
        assert dam.height == 110
        assert dam.year_built == 1988
        assert dam.river_name_el == "Κούρης"
        assert dam.type_el == "Λιθόρριπτο"
        assert dam.image_url == "https://example.com/kouris.jpg"
        assert dam.wikipedia_url == "https://el.wikipedia.org/wiki/Kouris"

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client({}, status_code=500)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_dams()

    async def test_empty_list_returns_empty(self):
        mock_client = _make_mock_client([])
        with patch("app.api_client._get_client", return_value=mock_client):
            result = await fetch_dams()
        assert result == []


# ── fetch_percentages ─────────────────────────────────────────────────────────

class TestFetchPercentages:
    _TARGET_DATE = date(2026, 2, 18)
    _PAYLOAD = {
        "date": "Feb 18, 2026 12:00:00 AM",
        "damNamesToPercentage": {
            "Kouris": 0.35,
            "Asprokremmos": 0.28,
        },
        "totalPercentage": 0.32,
        "totalCapacityInMCM": 327.0,
    }

    async def test_returns_percentage_snapshot(self):
        mock_client = _make_mock_client(self._PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            snap = await fetch_percentages(self._TARGET_DATE)

        assert snap.date == self._TARGET_DATE
        assert snap.total_percentage == pytest.approx(0.32)
        assert snap.total_capacity_mcm == pytest.approx(327.0)
        assert len(snap.dam_percentages) == 2

        by_name = {dp.dam_name_en: dp.percentage for dp in snap.dam_percentages}
        assert by_name["Kouris"] == pytest.approx(0.35)
        assert by_name["Asprokremmos"] == pytest.approx(0.28)

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client({}, status_code=503)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_percentages(self._TARGET_DATE)


# ── fetch_date_statistics ─────────────────────────────────────────────────────

class TestFetchDateStatistics:
    _TARGET_DATE = date(2026, 2, 18)
    _PAYLOAD = {
        "timestamp": 1739836800000,
        "date": "Feb 18, 2026 12:00:00 AM",
        "storageInMCM": {"Kouris": 40.25, "Asprokremmos": 15.1},
        "inflowInMCM": {"Kouris": 1.2, "Asprokremmos": 0.5},
    }

    async def test_returns_date_statistics(self):
        mock_client = _make_mock_client(self._PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            stats = await fetch_date_statistics(self._TARGET_DATE)

        assert stats.date == self._TARGET_DATE
        assert len(stats.dam_statistics) == 2

        by_name = {s.dam_name_en: s for s in stats.dam_statistics}
        assert by_name["Kouris"].storage_mcm == pytest.approx(40.25)
        assert by_name["Kouris"].inflow_mcm == pytest.approx(1.2)
        assert by_name["Asprokremmos"].storage_mcm == pytest.approx(15.1)

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client({}, status_code=404)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_date_statistics(self._TARGET_DATE)


# ── fetch_monthly_inflows ─────────────────────────────────────────────────────

class TestFetchMonthlyInflows:
    _PAYLOAD = [
        {"year": 2025, "period": "Nov", "periodOrder": 2, "inflowInMCM": 12.5},
        {"year": 2025, "period": "Dec", "periodOrder": 3, "inflowInMCM": 8.3},
    ]

    async def test_returns_monthly_inflows(self):
        mock_client = _make_mock_client(self._PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            inflows = await fetch_monthly_inflows()

        assert len(inflows) == 2
        assert inflows[0].year == 2025
        assert inflows[0].period == "Nov"
        assert inflows[0].period_order == 2
        assert inflows[0].inflow_mcm == pytest.approx(12.5)

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client([], status_code=500)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_monthly_inflows()


# ── fetch_events ──────────────────────────────────────────────────────────────

class TestFetchEvents:
    # Unix ms timestamps: 2020-01-01 00:00:00 UTC = 1577836800000
    #                     2020-12-31 00:00:00 UTC = 1609372800000
    _PAYLOAD = [
        {
            "nameEn": "Drought 2020",
            "nameEl": "Ξηρασία 2020",
            "type": "drought",
            "description": "Severe drought",
            "from": 1577836800000,
            "until": 1609372800000,
        }
    ]

    async def test_returns_water_events(self):
        mock_client = _make_mock_client(self._PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            events = await fetch_events(date(2020, 1, 1), date(2020, 12, 31))

        assert len(events) == 1
        ev = events[0]
        assert ev.name_en == "Drought 2020"
        assert ev.name_el == "Ξηρασία 2020"
        assert ev.event_type == "drought"
        assert ev.description == "Severe drought"
        assert ev.date_from == date(2020, 1, 1)
        assert ev.date_until == date(2020, 12, 31)

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client([], status_code=502)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_events(date(2020, 1, 1), date(2020, 12, 31))


# ── fetch_timeseries ──────────────────────────────────────────────────────────

class TestFetchTimeseries:
    _PAYLOAD = {
        "numOfDams": 17,
        "numOfPercentageEntries": 2,
        "dams": [],
        "percentages": {
            "2026-01-01": {
                "date": "Jan 01, 2026 12:00:00 AM",
                "damNamesToPercentage": {"Kouris": 0.40},
                "totalPercentage": 0.40,
                "totalCapacityInMCM": 327.0,
            },
            "2026-02-01": {
                "date": "Feb 01, 2026 12:00:00 AM",
                "damNamesToPercentage": {"Kouris": 0.38},
                "totalPercentage": 0.38,
                "totalCapacityInMCM": 327.0,
            },
        },
    }

    async def test_returns_sorted_snapshots(self):
        mock_client = _make_mock_client(self._PAYLOAD)
        with patch("app.api_client._get_client", return_value=mock_client):
            snapshots = await fetch_timeseries()

        assert len(snapshots) == 2
        # Must be sorted chronologically
        assert snapshots[0].date == date(2026, 1, 1)
        assert snapshots[1].date == date(2026, 2, 1)
        assert snapshots[0].total_percentage == pytest.approx(0.40)

    async def test_http_error_raises_upstream_api_error(self):
        mock_client = _make_mock_client({}, status_code=500)
        with patch("app.api_client._get_client", return_value=mock_client):
            with pytest.raises(UpstreamAPIError):
                await fetch_timeseries()
