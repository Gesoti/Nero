"""
Tests for the Germany data provider.
Data sources: Talsperrenleitzentrale Ruhr (9 dams), Sachsen LTV (48 dams).
MVP stub: downloads Ruhr page to verify connectivity, returns 0.0 for all dams.
"""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date

from app.providers.germany import (
    GermanyProvider,
    _GERMANY_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)


@pytest.fixture
def germany_provider() -> GermanyProvider:
    client = httpx.AsyncClient(base_url="https://www.talsperrenleitzentrale-ruhr.de")
    return GermanyProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_germany_provider_importable() -> None:
    from app.providers.germany import GermanyProvider
    assert GermanyProvider is not None


def test_germany_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = GermanyProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15(germany_provider: GermanyProvider) -> None:
    """Germany MVP has 15 hardcoded reservoir entries."""
    dams = await germany_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(germany_provider: GermanyProvider) -> None:
    """All dams must have coordinates within Germany's bounding box."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        # Germany bounding box: lat 47–55, lng 6–15
        assert 47.0 <= dam.lat <= 55.5, f"{dam.name_en} lat {dam.lat} outside Germany"
        assert 6.0 <= dam.lng <= 15.5, f"{dam.name_en} lng {dam.lng} outside Germany"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(germany_provider: GermanyProvider) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_positive_capacity(germany_provider: GermanyProvider) -> None:
    """All dams must have a positive capacity in MCM."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has zero capacity"


@pytest.mark.asyncio
async def test_fetch_dams_expected_names_present(germany_provider: GermanyProvider) -> None:
    """Verify key reservoir name_en values are present."""
    dams = await germany_provider.fetch_dams()
    names = {d.name_en for d in dams}
    expected_subset = {"Bleiloch", "Edersee", "Bigge", "Mohne", "Hohenwarte"}
    assert expected_subset.issubset(names), f"Missing: {expected_subset - names}"


@pytest.mark.asyncio
async def test_fetch_dams_bleiloch_is_largest(germany_provider: GermanyProvider) -> None:
    """Bleiloch (215 MCM) should be the largest reservoir in the list."""
    dams = await germany_provider.fetch_dams()
    max_dam = max(dams, key=lambda d: d.capacity_mcm)
    assert max_dam.name_en == "Bleiloch"


# ── fetch_percentages stub tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot(germany_provider: GermanyProvider) -> None:
    """Stub returns a valid PercentageSnapshot with 15 entries."""
    result = await germany_provider.fetch_percentages(date(2026, 3, 16))
    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_all_zero(germany_provider: GermanyProvider) -> None:
    """Stub returns 0.0 for all percentages (parsing TBD)."""
    result = await germany_provider.fetch_percentages(date(2026, 3, 16))
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0, f"{dp.dam_name_en} has non-zero percentage in stub"


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target(germany_provider: GermanyProvider) -> None:
    """Snapshot date must match the requested target date."""
    target = date(2026, 3, 16)
    result = await germany_provider.fetch_percentages(target)
    assert result.date == target


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, stub still returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = GermanyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


# ── fetch_date_statistics stub tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_15_entries(germany_provider: GermanyProvider) -> None:
    """fetch_date_statistics must return stats for all 15 dams."""
    result = await germany_provider.fetch_date_statistics(date(2026, 3, 16))
    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15


@pytest.mark.asyncio
async def test_fetch_date_statistics_all_zero(germany_provider: GermanyProvider) -> None:
    """Stub returns 0.0 storage for all dams."""
    result = await germany_provider.fetch_date_statistics(date(2026, 3, 16))
    for stat in result.dam_statistics:
        assert stat.storage_mcm == 0.0


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
