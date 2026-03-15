"""
Tests for the Bulgaria data provider.
Data source: MOEW (Ministry of Environment and Water) daily bulletin.
Bulgaria's 20 largest reservoirs are hardcoded; parsing the .doc format
is a future improvement — for MVP the provider returns 0.0 fallback values.
"""
from __future__ import annotations

import httpx
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.providers.bulgaria import (
    BulgariaProvider,
    _BULGARIA_DAMS,
    _BULLETIN_URL_TEMPLATE,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)


@pytest.fixture
def bulgaria_provider() -> BulgariaProvider:
    client = httpx.AsyncClient(base_url="https://www.moew.government.bg")
    return BulgariaProvider(client=client)


# ── Protocol compliance ───────────────────────────────────────────────────────

def test_bulgaria_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = BulgariaProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_20_reservoirs(bulgaria_provider: BulgariaProvider) -> None:
    dams = await bulgaria_provider.fetch_dams()
    assert len(dams) == 20


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(bulgaria_provider: BulgariaProvider) -> None:
    """All reservoirs must fall within Bulgaria's geographic bounding box."""
    dams = await bulgaria_provider.fetch_dams()
    for dam in dams:
        assert 41.0 <= dam.lat <= 44.5, f"{dam.name_en} lat {dam.lat} outside Bulgaria"
        assert 22.0 <= dam.lng <= 29.0, f"{dam.name_en} lng {dam.lng} outside Bulgaria"


@pytest.mark.asyncio
async def test_fetch_dams_iskar_is_largest(bulgaria_provider: BulgariaProvider) -> None:
    """Iskar (655.3 MCM) must be the largest reservoir in the list."""
    dams = await bulgaria_provider.fetch_dams()
    iskar = next((d for d in dams if d.name_en == "Iskar"), None)
    assert iskar is not None, "Iskar not found in dam list"
    assert iskar.capacity_mcm == 655.3


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(bulgaria_provider: BulgariaProvider) -> None:
    dams = await bulgaria_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity_mcm=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_name_el(bulgaria_provider: BulgariaProvider) -> None:
    """Every dam must have a Bulgarian (Cyrillic) display name."""
    dams = await bulgaria_provider.fetch_dams()
    for dam in dams:
        assert dam.name_el, f"{dam.name_en} has empty name_el"


# ── URL template ──────────────────────────────────────────────────────────────

def test_bulletin_url_template_contains_date_placeholder() -> None:
    """The URL template must contain a {date} placeholder for DDMMYYYY format."""
    assert "{date}" in _BULLETIN_URL_TEMPLATE


def test_bulletin_url_template_contains_moew_domain() -> None:
    assert "moew.government.bg" in _BULLETIN_URL_TEMPLATE


# ── fetch_percentages (stub — returns 0.0 fallback) ──────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    """fetch_percentages returns a PercentageSnapshot even when parsing not implemented."""
    mock_response = httpx.Response(
        200,
        content=b"\xd0\xcf\x11\xe0" + b"\x00" * 512,  # minimal .doc magic bytes
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 20


@pytest.mark.asyncio
async def test_fetch_percentages_all_zero_while_parsing_stub() -> None:
    """MVP stub: all percentages are 0.0 since .doc parsing is not yet implemented."""
    mock_response = httpx.Response(
        200,
        content=b"\xd0\xcf\x11\xe0" + b"\x00" * 512,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    for dp in result.dam_percentages:
        assert dp.percentage == 0.0, f"{dp.dam_name_en} returned non-zero percentage"


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_http_error() -> None:
    """On HTTP 4xx/5xx, provider returns zero-fill snapshot rather than raising."""
    mock_response = httpx.Response(
        404,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 20
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network failure, provider returns zero-fill snapshot rather than raising."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target() -> None:
    mock_response = httpx.Response(
        200,
        content=b"\x00" * 100,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    target = date(2026, 3, 14)
    result = await provider.fetch_percentages(target)
    assert result.date == target


# ── fetch_date_statistics ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats_for_all_dams() -> None:
    mock_response = httpx.Response(
        200,
        content=b"\x00" * 100,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = BulgariaProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 20


# ── Stub methods ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(bulgaria_provider: BulgariaProvider) -> None:
    result = await bulgaria_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(bulgaria_provider: BulgariaProvider) -> None:
    result = await bulgaria_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []


@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(bulgaria_provider: BulgariaProvider) -> None:
    result = await bulgaria_provider.fetch_timeseries()
    assert result == []
