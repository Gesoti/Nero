"""
Tests for the Norway data provider.
Data source: NVE Magasinstatistikk API (Norwegian Water Resources and Energy Directorate).
Norway publishes hydropower reservoir fill data aggregated into 5 electricity price zones
(NO1–NO5) rather than individual reservoirs.
"""
from __future__ import annotations

import json
import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date

from app.providers.norway import (
    NorwayProvider,
    _NORWAY_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)


# Minimal mock JSON returned by HentOffentligDataSisteUke.
# Includes 5 EL zones + 1 national total (omrType="NO") which must be filtered out.
_MOCK_NVE_JSON = json.dumps([
    {"dato_Id": "2026-03-10", "omrType": "EL", "omrnr": 1, "fyllingsgrad": 0.52,
     "kapasitet_TWh": 11.2, "fylling_TWh": 5.86, "endring_fyllingsgrad": -0.01},
    {"dato_Id": "2026-03-10", "omrType": "EL", "omrnr": 2, "fyllingsgrad": 0.68,
     "kapasitet_TWh": 33.5, "fylling_TWh": 22.78, "endring_fyllingsgrad": 0.02},
    {"dato_Id": "2026-03-10", "omrType": "EL", "omrnr": 3, "fyllingsgrad": 0.45,
     "kapasitet_TWh": 10.1, "fylling_TWh": 4.55, "endring_fyllingsgrad": -0.005},
    {"dato_Id": "2026-03-10", "omrType": "EL", "omrnr": 4, "fyllingsgrad": 0.71,
     "kapasitet_TWh": 18.3, "fylling_TWh": 12.99, "endring_fyllingsgrad": 0.01},
    {"dato_Id": "2026-03-10", "omrType": "EL", "omrnr": 5, "fyllingsgrad": 0.55,
     "kapasitet_TWh": 14.8, "fylling_TWh": 8.14, "endring_fyllingsgrad": -0.02},
    {"dato_Id": "2026-03-10", "omrType": "NO", "omrnr": 0, "fyllingsgrad": 0.58,
     "kapasitet_TWh": 87.9, "fylling_TWh": 51.0, "endring_fyllingsgrad": -0.005},
])


@pytest.fixture
def norway_provider() -> NorwayProvider:
    client = httpx.AsyncClient(base_url="https://biapi.nve.no")
    return NorwayProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_norway_provider_importable() -> None:
    from app.providers.norway import NorwayProvider
    assert NorwayProvider is not None


def test_norway_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = NorwayProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_5_zones(norway_provider: NorwayProvider) -> None:
    """Norway data is published as 5 electricity price zones — no individual reservoirs."""
    dams = await norway_provider.fetch_dams()
    assert len(dams) == 5


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(norway_provider: NorwayProvider) -> None:
    """All zones must have non-zero coordinates within Norway's bounding box."""
    dams = await norway_provider.fetch_dams()
    for dam in dams:
        # Norway bounding box: lat 57–72, lng 4–31
        assert 57.0 <= dam.lat <= 72.0, f"{dam.name_en} lat {dam.lat} outside Norway"
        assert 4.0 <= dam.lng <= 31.0, f"{dam.name_en} lng {dam.lng} outside Norway"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(norway_provider: NorwayProvider) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await norway_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(norway_provider: NorwayProvider) -> None:
    """All zones must have a positive capacity."""
    dams = await norway_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has zero capacity"


@pytest.mark.asyncio
async def test_fetch_dams_zone_names_present(norway_provider: NorwayProvider) -> None:
    """Verify all 5 expected zone name_en values are present."""
    dams = await norway_provider.fetch_dams()
    names = {d.name_en for d in dams}
    expected = {"NO1-East", "NO2-Southwest", "NO3-Central", "NO4-North", "NO5-West"}
    assert names == expected


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    """On valid API response, fetch_percentages returns a PercentageSnapshot with 5 entries."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 5


@pytest.mark.asyncio
async def test_fetch_percentages_percentages_in_valid_range() -> None:
    """All returned percentages must be in [0, 1] range."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    for dp in result.dam_percentages:
        assert 0.0 <= dp.percentage <= 1.0, (
            f"{dp.dam_name_en} percentage {dp.percentage} outside [0, 1]"
        )


@pytest.mark.asyncio
async def test_fetch_percentages_filters_out_national_total() -> None:
    """The national total (omrType='NO') must not appear in dam_percentages."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    # Exactly 5 EL zones — national aggregate omitted
    assert len(result.dam_percentages) == 5


@pytest.mark.asyncio
async def test_fetch_percentages_values_match_api() -> None:
    """Percentages should match fyllingsgrad values from the mock API response."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    pct_map = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    assert abs(pct_map["NO1-East"] - 0.52) < 0.001
    assert abs(pct_map["NO2-Southwest"] - 0.68) < 0.001


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_http_error() -> None:
    """On HTTP error, fetch_percentages returns zero-fill defaults (does not raise)."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 5
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, fetch_percentages returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 10))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 5
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target() -> None:
    """Snapshot date must match the requested target date."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    target = date(2026, 3, 10)
    result = await provider.fetch_percentages(target)
    assert result.date == target


# ── fetch_date_statistics tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_5_entries() -> None:
    """fetch_date_statistics must return stats for all 5 zones."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 10))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 5


@pytest.mark.asyncio
async def test_fetch_date_statistics_storage_mcm_positive() -> None:
    """Storage values derived from fylling_TWh must be positive for non-zero fill."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_NVE_JSON,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://biapi.nve.no"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = NorwayProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 10))

    for stat in result.dam_statistics:
        assert stat.storage_mcm >= 0.0, f"{stat.dam_name_en} has negative storage"


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(norway_provider: NorwayProvider) -> None:
    result = await norway_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(norway_provider: NorwayProvider) -> None:
    result = await norway_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(norway_provider: NorwayProvider) -> None:
    result = await norway_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
