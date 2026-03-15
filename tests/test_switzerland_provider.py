"""
Tests for the Switzerland data provider.
Data source: BFE/SFOE CSV (Bundesamt für Energie / Swiss Federal Office of Energy).
Switzerland publishes hydropower reservoir fill data aggregated into 4 regions
(Wallis, Graubuenden, Tessin, UebrigCH) plus a national total.
"""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date

from app.providers.switzerland import (
    SwitzerlandProvider,
    _SWITZERLAND_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)


# Mock CSV matching the format specified in the task brief.
# Two rows: older data first, latest data last (provider reads last row for current state).
_MOCK_CSV = (
    "Datum,Wallis_speicherinhalt_gwh,Graubuenden_speicherinhalt_gwh,"
    "Tessin_speicherinhalt_gwh,UebrigCH_speicherinhalt_gwh,"
    "TotalCH_speicherinhalt_gwh,Wallis_max_speicherinhalt_gwh,"
    "Graubuenden_max_speicherinhalt_gwh,Tessin_max_speicherinhalt_gwh,"
    "UebrigCH_max_speicherinhalt_gwh,TotalCH_max_speicherinhalt_gwh\n"
    "2026-03-02,860.0,420.0,240.0,260.0,1780.0,4300.0,2100.0,1200.0,1300.0,8900.0\n"
    "2026-03-09,840.0,410.0,235.0,255.0,1740.0,4300.0,2100.0,1200.0,1300.0,8900.0\n"
)

# Known-values row for percentage verification:
# Wallis: 840 / 4300 ≈ 0.19535, Graubuenden: 410 / 2100 ≈ 0.19524,
# Tessin: 235 / 1200 ≈ 0.19583, UebrigCH: 255 / 1300 ≈ 0.19615
_WALLIS_EXPECTED_PCT = 840.0 / 4300.0
_GRAUBUENDEN_EXPECTED_PCT = 410.0 / 2100.0


@pytest.fixture
def switzerland_provider() -> SwitzerlandProvider:
    client = httpx.AsyncClient(base_url="https://uvek-gis.admin.ch")
    return SwitzerlandProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_switzerland_provider_importable() -> None:
    from app.providers.switzerland import SwitzerlandProvider
    assert SwitzerlandProvider is not None


def test_switzerland_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = SwitzerlandProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_4_regions(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    """Switzerland data is published as 4 regions — not individual reservoirs."""
    dams = await switzerland_provider.fetch_dams()
    assert len(dams) == 4


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    """All regions must have coordinates within Switzerland's bounding box."""
    dams = await switzerland_provider.fetch_dams()
    for dam in dams:
        # Switzerland bounding box: lat 45.8–47.8, lng 5.9–10.5
        assert 45.0 <= dam.lat <= 48.0, f"{dam.name_en} lat {dam.lat} outside Switzerland"
        assert 5.0 <= dam.lng <= 11.0, f"{dam.name_en} lng {dam.lng} outside Switzerland"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await switzerland_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_positive_capacity(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    """All regions must have a positive capacity in hm³."""
    dams = await switzerland_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has zero capacity"


@pytest.mark.asyncio
async def test_fetch_dams_region_names_present(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    """Verify all 4 expected region name_en values are present."""
    dams = await switzerland_provider.fetch_dams()
    names = {d.name_en for d in dams}
    expected = {"Wallis", "Graubuenden", "Tessin", "UebrigCH"}
    assert names == expected


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    """On valid CSV response, fetch_percentages returns a PercentageSnapshot with 4 entries."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 4


@pytest.mark.asyncio
async def test_fetch_percentages_computes_correct_percentage() -> None:
    """Percentages should be computed as speicherinhalt / max_speicherinhalt."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    pct_map = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    assert abs(pct_map["Wallis"] - _WALLIS_EXPECTED_PCT) < 0.0001
    assert abs(pct_map["Graubuenden"] - _GRAUBUENDEN_EXPECTED_PCT) < 0.0001


@pytest.mark.asyncio
async def test_fetch_percentages_reads_last_row() -> None:
    """Provider must use the latest (last) data row, not the first."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    # Last row has Wallis=840, first row has Wallis=860 — must use 840
    pct_map = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    # 840/4300 ≈ 0.19535, NOT 860/4300 ≈ 0.20
    assert pct_map["Wallis"] < 860.0 / 4300.0 + 0.0001


@pytest.mark.asyncio
async def test_fetch_percentages_percentages_in_valid_range() -> None:
    """All returned percentages must be in [0, 1] range."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    for dp in result.dam_percentages:
        assert 0.0 <= dp.percentage <= 1.0, (
            f"{dp.dam_name_en} percentage {dp.percentage} outside [0, 1]"
        )


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_http_error() -> None:
    """On HTTP error, fetch_percentages returns zero-fill defaults (does not raise)."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 4
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, fetch_percentages returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    assert isinstance(result, PercentageSnapshot)
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target() -> None:
    """Snapshot date must match the requested target date."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    target = date(2026, 3, 9)
    result = await provider.fetch_percentages(target)
    assert result.date == target


# ── fetch_timeseries tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_historical_snapshots() -> None:
    """fetch_timeseries must return one PercentageSnapshot per CSV data row."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_timeseries()

    # Mock CSV has 2 data rows (excluding header)
    assert len(result) == 2
    for snap in result:
        assert isinstance(snap, PercentageSnapshot)
        assert len(snap.dam_percentages) == 4


@pytest.mark.asyncio
async def test_fetch_timeseries_dates_parsed_correctly() -> None:
    """Timeseries snapshots must carry the date from the CSV Datum column."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_timeseries()

    dates = [snap.date for snap in result]
    assert date(2026, 3, 2) in dates
    assert date(2026, 3, 9) in dates


@pytest.mark.asyncio
async def test_fetch_timeseries_graceful_on_http_error() -> None:
    """On HTTP error, fetch_timeseries returns empty list (does not raise)."""
    mock_response = httpx.Response(
        503,
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_timeseries()
    assert result == []


# ── fetch_date_statistics tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_4_entries() -> None:
    """fetch_date_statistics must return stats for all 4 regions."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 9))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 4


@pytest.mark.asyncio
async def test_fetch_date_statistics_storage_mcm_positive() -> None:
    """Storage_mcm must be positive for non-zero GWh values."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        headers={"content-type": "text/csv"},
        request=httpx.Request("GET", "https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = SwitzerlandProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 9))

    for stat in result.dam_statistics:
        assert stat.storage_mcm >= 0.0, f"{stat.dam_name_en} has negative storage"


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    result = await switzerland_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(
    switzerland_provider: SwitzerlandProvider,
) -> None:
    result = await switzerland_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
