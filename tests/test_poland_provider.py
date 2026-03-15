"""
Tests for the Poland data provider.
Data source: IMGW daily PDF bulletin (19 reservoirs).
MVP stub: downloads IMGW PDF to verify connectivity, returns 0.0 for all dams.
"""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date

from app.providers.poland import (
    PolandProvider,
    _POLAND_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)


@pytest.fixture
def poland_provider() -> PolandProvider:
    client = httpx.AsyncClient(base_url="https://res2.imgw.pl")
    return PolandProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_poland_provider_importable() -> None:
    from app.providers.poland import PolandProvider
    assert PolandProvider is not None


def test_poland_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = PolandProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15(poland_provider: PolandProvider) -> None:
    """Poland MVP has 15 hardcoded reservoir entries."""
    dams = await poland_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(poland_provider: PolandProvider) -> None:
    """All dams must have coordinates within Poland's bounding box."""
    dams = await poland_provider.fetch_dams()
    for dam in dams:
        # Poland bounding box: lat 49–55, lng 14–24
        assert 49.0 <= dam.lat <= 55.0, f"{dam.name_en} lat {dam.lat} outside Poland"
        assert 14.0 <= dam.lng <= 24.5, f"{dam.name_en} lng {dam.lng} outside Poland"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(poland_provider: PolandProvider) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await poland_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_positive_capacity(poland_provider: PolandProvider) -> None:
    """All dams must have a positive capacity in MCM."""
    dams = await poland_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has zero capacity"


@pytest.mark.asyncio
async def test_fetch_dams_expected_names_present(poland_provider: PolandProvider) -> None:
    """Verify key reservoir name_en values are present."""
    dams = await poland_provider.fetch_dams()
    names = {d.name_en for d in dams}
    expected_subset = {"Solina", "Wloclawek", "Czorsztyn", "Jeziorsko"}
    assert expected_subset.issubset(names), f"Missing: {expected_subset - names}"


@pytest.mark.asyncio
async def test_fetch_dams_solina_is_largest(poland_provider: PolandProvider) -> None:
    """Solina (472 MCM) should be the largest reservoir in the list."""
    dams = await poland_provider.fetch_dams()
    max_dam = max(dams, key=lambda d: d.capacity_mcm)
    assert max_dam.name_en == "Solina"


# ── fetch_percentages stub tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot(poland_provider: PolandProvider) -> None:
    """Stub returns a valid PercentageSnapshot with 15 entries."""
    result = await poland_provider.fetch_percentages(date(2026, 3, 16))
    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_all_zero(poland_provider: PolandProvider) -> None:
    """Stub returns 0.0 for all percentages (PDF parsing TBD)."""
    result = await poland_provider.fetch_percentages(date(2026, 3, 16))
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0, f"{dp.dam_name_en} has non-zero percentage in stub"


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target(poland_provider: PolandProvider) -> None:
    """Snapshot date must match the requested target date."""
    target = date(2026, 3, 16)
    result = await poland_provider.fetch_percentages(target)
    assert result.date == target


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, stub still returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = PolandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


# ── fetch_date_statistics stub tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_15_entries(poland_provider: PolandProvider) -> None:
    """fetch_date_statistics must return stats for all 15 dams."""
    result = await poland_provider.fetch_date_statistics(date(2026, 3, 16))
    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15


@pytest.mark.asyncio
async def test_fetch_date_statistics_all_zero(poland_provider: PolandProvider) -> None:
    """Stub returns 0.0 storage for all dams."""
    result = await poland_provider.fetch_date_statistics(date(2026, 3, 16))
    for stat in result.dam_statistics:
        assert stat.storage_mcm == 0.0


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(poland_provider: PolandProvider) -> None:
    result = await poland_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(poland_provider: PolandProvider) -> None:
    result = await poland_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(poland_provider: PolandProvider) -> None:
    result = await poland_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
